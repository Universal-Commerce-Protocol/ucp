/**
 * @param {Object} params
 * @param {import('@actions/github').GitHub} params.github
 * @param {import('@actions/github').Context} params.context
 */
module.exports = async function triageAutomation({ github, context }) {
  const { owner, repo } = context.repo;
  const eventName = context.eventName;
  
  // Label Constants
  const LABEL_NEEDS_TRIAGE = 'status:needs-triage';
  const LABEL_UNDER_REVIEW = 'status:under-review';
  const LABEL_BLOCKED = 'blocked';
  const LABEL_DEVOPS = 'devops';
  const PREFIX_AREA = 'area:';

  // Extract associated Pull Request number from event payload
  const prNumber =
    context.payload.pull_request?.number ||
    context.payload.issue?.number ||
    context.payload.check_suite?.pull_requests?.[0]?.number;

  if (!prNumber) {
    console.log('[SKIP] Not associated with an open Pull Request.');
    return;
  }

  // Fetch the full pull request details to check draft and CI checks status
  const { data: pr } = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: prNumber
  });

  // 1. Verify draft status
  if (pr.draft) {
    console.log(`[SKIP] PR #${prNumber} is a draft.`);
    return;
  }

  // 2. Verify CI Checks have successfully completed and passed
  const ciPassed = await checkCIPassed(
    github,
    owner,
    repo,
    pr.head.sha,
    context.workflow
  );

  if (!ciPassed) {
    console.log(`[SKIP] PR #${prNumber} has pending or failed CI checks.`);
    return;
  }

  console.log(
    `[START] Event "${eventName}" ` +
    `(action: "${context.payload.action}") for PR #${prNumber}`
  );
  let actionTaken = 'No labeling changes required';
  const labels = pr.labels.map(l => l.name);

  // Ingestion: Run when CI completes on new PR, or ready_for_review
  const isIngestTrigger =
    (eventName === 'pull_request' &&
      (context.payload.action === 'opened' ||
        context.payload.action === 'ready_for_review')) ||
    eventName === 'check_suite';

  if (isIngestTrigger) {
    // Only ingest if the PR is not already under review
    if (!labels.includes(LABEL_UNDER_REVIEW)) {
      if (!labels.includes(LABEL_NEEDS_TRIAGE)) {
        console.log(`[ACTION] Ingesting PR: adding ${LABEL_NEEDS_TRIAGE}`);
        await github.rest.issues.addLabels({
          owner,
          repo,
          issue_number: prNumber,
          labels: [LABEL_NEEDS_TRIAGE]
        });
        actionTaken = `Ingested: added ${LABEL_NEEDS_TRIAGE}`;
      }
    }
  }

  // Triage & Feedback Loops triggered by manually labeling
  if (eventName === 'pull_request' && context.payload.action === 'labeled') {
    const labelAdded = context.payload.label.name;
    console.log(`[INFO] Label added: ${labelAdded}`);

    // Area or DevOps Label: Move from needs-triage to under-review
    if (labelAdded.startsWith(PREFIX_AREA) || labelAdded === LABEL_DEVOPS) {
      console.log(
        `[ACTION] Triage label detected. ` +
        `Applying ${LABEL_UNDER_REVIEW} and removing ${LABEL_NEEDS_TRIAGE}`
      );

      if (!labels.includes(LABEL_UNDER_REVIEW)) {
        await github.rest.issues.addLabels({
          owner,
          repo,
          issue_number: prNumber,
          labels: [LABEL_UNDER_REVIEW]
        });
      }
      if (labels.includes(LABEL_NEEDS_TRIAGE)) {
        await github.rest.issues.removeLabel({
          owner,
          repo,
          issue_number: prNumber,
          name: LABEL_NEEDS_TRIAGE
        });
      }
      actionTaken =
        `Triaged: added ${LABEL_UNDER_REVIEW}, ` +
        `removed ${LABEL_NEEDS_TRIAGE}`;
    }

    // Blocked Label: Suspend under-review
    if (labelAdded === LABEL_BLOCKED) {
      console.log(`[ACTION] Blocked label detected. Removing ${LABEL_UNDER_REVIEW}`);
      if (labels.includes(LABEL_UNDER_REVIEW)) {
        await github.rest.issues.removeLabel({
          owner,
          repo,
          issue_number: prNumber,
          name: LABEL_UNDER_REVIEW
        });
        actionTaken = `Blocked: removed ${LABEL_UNDER_REVIEW}`;
      } else {
        actionTaken = `Blocked: ${LABEL_UNDER_REVIEW} was already absent`;
      }
    }
  }

  // Resume via Commit pushed on blocked PR
  if (eventName === 'pull_request' && context.payload.action === 'synchronize') {
    console.log(
      `[INFO] PR synchronized (new commit pushed). Checking blockage status.`
    );

    if (labels.includes(LABEL_BLOCKED)) {
      console.log(
        `[ACTION] Blocked PR resumed. ` +
        `Removing ${LABEL_BLOCKED} and adding ${LABEL_UNDER_REVIEW}`
      );
      if (!labels.includes(LABEL_UNDER_REVIEW)) {
        await github.rest.issues.addLabels({
          owner,
          repo,
          issue_number: prNumber,
          labels: [LABEL_UNDER_REVIEW]
        });
      }
      await github.rest.issues.removeLabel({
        owner,
        repo,
        issue_number: prNumber,
        name: LABEL_BLOCKED
      });
      actionTaken =
        `Resumed: added ${LABEL_UNDER_REVIEW}, ` +
        `removed ${LABEL_BLOCKED}`;
    }
  }

  // Resume via Comment (Author comments on a blocked PR)
  if (
    eventName === 'issue_comment' &&
    context.payload.action === 'created'
  ) {
    console.log(`[INFO] Comment created. Checking author response on blocked PR.`);
    const commentAuthor = context.payload.comment.user.login;
    const prAuthor = pr.user.login;

    if (commentAuthor === prAuthor && labels.includes(LABEL_BLOCKED)) {
      console.log(
        `[ACTION] Author commented on blocked PR. ` +
        `Removing ${LABEL_BLOCKED} and adding ${LABEL_UNDER_REVIEW}`
      );
      if (!labels.includes(LABEL_UNDER_REVIEW)) {
        await github.rest.issues.addLabels({
          owner,
          repo,
          issue_number: prNumber,
          labels: [LABEL_UNDER_REVIEW]
        });
      }
      await github.rest.issues.removeLabel({
        owner,
        repo,
        issue_number: prNumber,
        name: LABEL_BLOCKED
      });
      actionTaken =
        `Resumed via comment: added ${LABEL_UNDER_REVIEW}, ` +
        `removed ${LABEL_BLOCKED}`;
    }
  }

  console.log('\n========================================');
  console.log('     TRIAGE AUTOMATION RUN SUMMARY');
  console.log('========================================');
  console.log(`PR Number:    #${prNumber}`);
  console.log(`Event:        ${eventName}`);
  console.log(`Result:       ${actionTaken}`);
  console.log('========================================\n');
}

/**
 * Checks if all CI statuses and check runs have passed successfully for a ref.
 */
async function checkCIPassed(github, owner, repo, ref, workflowName) {
  // 1. Check combined status (classic Statuses API)
  const { data: statusData } = await github.rest.repos.getCombinedStatusForRef({
    owner,
    repo,
    ref
  });
  if (statusData.state !== 'success' && statusData.statuses.length > 0) {
    console.log(`[INFO] Combined status state is currently: "${statusData.state}"`);
    return false;
  }

  // 2. Check check runs (modern Checks API)
  const { data: checksData } = await github.rest.checks.listForRef({
    owner,
    repo,
    ref
  });
  const runs = checksData.check_runs;
  if (runs.length === 0) return true;

  const pendingOrFailed = [];
  for (const run of runs) {
    // Skip checking this workflow run itself to avoid deadlock
    if (run.name.includes(workflowName) || run.name.includes('Triage')) {
      continue;
    }

    if (run.status !== 'completed') {
      pendingOrFailed.push(`${run.name} (pending)`);
    } else {
      const acceptableConclusions = ['success', 'skipped', 'neutral'];
      if (!acceptableConclusions.includes(run.conclusion)) {
        pendingOrFailed.push(`${run.name} (${run.conclusion})`);
      }
    }
  }

  if (pendingOrFailed.length > 0) {
    console.log(
      `[INFO] PR head has pending or failed checks: ` +
      `${pendingOrFailed.join(', ')}`
    );
    return false;
  }

  return true;
}
