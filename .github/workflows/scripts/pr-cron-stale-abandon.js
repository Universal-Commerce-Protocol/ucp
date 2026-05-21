/* eslint-disable no-console */
/**
 * @param {Object} params
 * @param {import('@actions/github').GitHub} params.github
 * @param {import('@actions/github').Context} params.context
 * @param {import('@actions/core')} params.core
 */
module.exports = async function staleTracker({ github, context, core }) {
  const { owner, repo } = context.repo;
  const STALE_THRESHOLD_DAYS = 30;
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - STALE_THRESHOLD_DAYS);

  console.log(`Scanning for open pull requests with no activity since ${thirtyDaysAgo.toISOString()}`);

  // Query active PRs
  const pulls = await github.rest.pulls.list({
    owner,
    repo,
    state: 'open',
    per_page: 100
  });

  console.log(`Found ${pulls.data.length} open pull requests to check.`);

  for (const pr of pulls.data) {
    const labels = pr.labels.map(l => l.name);
    const updatedDate = new Date(pr.updated_at);
    const isInactive = updatedDate < thirtyDaysAgo;

    if (isInactive) {
      console.log(`PR #${pr.number} "${pr.title}" is inactive since ${pr.updated_at}`);
      
      // 5. Feedback Loop - Stale
      if (labels.includes('status:under-review')) {
        console.log(`Applying status:stale-review and status:needs-triage to PR #${pr.number}`);
        await github.rest.issues.addLabels({
          owner,
          repo,
          issue_number: pr.number,
          labels: ['status:stale-review', 'status:needs-triage']
        });
      }

      // 6. Feedback Loop - Abandon
      if (labels.includes('blocked')) {
        console.log(`Applying status:stale-review, status:abandon-candidate and status:needs-triage to PR #${pr.number}`);
        await github.rest.issues.addLabels({
          owner,
          repo,
          issue_number: pr.number,
          labels: ['status:stale-review', 'status:abandon-candidate', 'status:needs-triage']
        });
      }
    }
  }
}
