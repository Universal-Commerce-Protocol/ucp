/**
 * @param {Object} params
 * @param {import('@actions/github').GitHub} params.github
 * @param {import('@actions/github').Context} params.context
 */
module.exports = async function staleTracker({ github, context }) {
  const { owner, repo } = context.repo;

  // Threshold Config (abandon is an additional 30 days on top of stale)
  const STALE_THRESHOLD_DAYS = 30;
  const ADDITIONAL_ABANDON_DAYS = 30;
  const ABANDON_THRESHOLD_DAYS =
    STALE_THRESHOLD_DAYS + ADDITIONAL_ABANDON_DAYS;

  // Label Constants
  const LABEL_UNDER_REVIEW = 'status:under-review';
  const LABEL_BLOCKED = 'blocked';
  const LABEL_STALE_REVIEW = 'status:stale-review';
  const LABEL_NEEDS_TRIAGE = 'status:needs-triage';
  const LABEL_ABANDON_CANDIDATE = 'status:abandon-candidate';

  const staleLimit =
    new Date(Date.now() - STALE_THRESHOLD_DAYS * 24 * 60 * 60 * 1000);
  const abandonLimit =
    new Date(Date.now() - ABANDON_THRESHOLD_DAYS * 24 * 60 * 60 * 1000);

  console.log(`[CONFIG] Stale limit: >${STALE_THRESHOLD_DAYS} days (${staleLimit.toISOString()})`);
  console.log(`[CONFIG] Abandon limit: >${ABANDON_THRESHOLD_DAYS} days (${abandonLimit.toISOString()})`);

  // Use native Octokit paginate to list ALL open pull requests
  const pulls = await github.paginate(github.rest.pulls.list, {
    owner,
    repo,
    state: 'open',
    per_page: 100
  });
  const totalScanned = pulls.length;

  let staleFound = 0, staleLabeled = 0, abandonFound = 0, abandonLabeled = 0;
  let alreadyLabeledCount = 0;

  console.log(`[FETCH] Retrieved ${totalScanned} open PRs to evaluate.`);

  for (const pr of pulls) {
    const updatedDate = new Date(pr.updated_at);
    const labels = pr.labels.map(l => l.name);

    const isStale = updatedDate < staleLimit;
    const isAbandonCandidate = updatedDate < abandonLimit;

    // Determine matching category
    const isStaleReview = isStale && labels.includes(LABEL_UNDER_REVIEW);
    const isBlockedAbandon =
      isAbandonCandidate && labels.includes(LABEL_BLOCKED);

    if (!isStaleReview && !isBlockedAbandon) continue;

    console.log(
      `[INACTIVE] PR #${pr.number} "${pr.title}" ` +
      `is inactive since ${pr.updated_at}`
    );

    // Select target labels based on matching category
    const targetLabels = isBlockedAbandon
      ? [LABEL_STALE_REVIEW, LABEL_ABANDON_CANDIDATE, LABEL_NEEDS_TRIAGE]
      : [LABEL_STALE_REVIEW, LABEL_NEEDS_TRIAGE];

    if (isStaleReview) staleFound++;
    if (isBlockedAbandon) abandonFound++;

    // Keep only labels that are missing from the PR
    const missingLabels = targetLabels.filter(l => !labels.includes(l));

    if (missingLabels.length > 0) {
      console.log(
        `[ACTION] PR #${pr.number} "${pr.title}" is inactive. ` +
        `Adding missing labels: ${missingLabels}`
      );
      await github.rest.issues.addLabels({
        owner,
        repo,
        issue_number: pr.number,
        labels: missingLabels
      });

      if (isStaleReview) staleLabeled++;
      if (isBlockedAbandon) abandonLabeled++;
    } else {
      alreadyLabeledCount++;
    }
  }

  console.log('\n========================================');
  console.log('     STALE TRACKER RUN SUMMARY');
  console.log('========================================');
  console.log(`Total Open PRs Scanned:          ${totalScanned}`);
  console.log(`PRs Already Correctly Labeled:   ${alreadyLabeledCount}`);
  console.log('----------------------------------------');
  console.log(
    `Stale Reviews (>${STALE_THRESHOLD_DAYS}d) Found:      ` +
    `${staleFound}`
  );
  console.log(`Stale Reviews Newly Labeled:     ${staleLabeled}`);
  console.log('----------------------------------------');
  console.log(
    `Abandon Candidates (>${ABANDON_THRESHOLD_DAYS}d) Found:  ` +
    `${abandonFound}`
  );
  console.log(`Abandon Candidates Newly Labeled: ${abandonLabeled}`);
  console.log('========================================\n');
}
