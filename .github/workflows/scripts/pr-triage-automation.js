/* eslint-disable no-console */
/**
 * @param {Object} params
 * @param {import('@actions/github').GitHub} params.github
 * @param {import('@actions/github').Context} params.context
 * @param {import('@actions/core')} params.core
 */
module.exports = async function triageAutomation({ github, context, core }) {
  const { owner, repo } = context.repo;
  const eventName = context.eventName;
  
  let prNumber;
  if (context.payload.pull_request) {
    prNumber = context.payload.pull_request.number;
  } else if (context.payload.issue && context.payload.issue.pull_request) {
    prNumber = context.payload.issue.number;
  } else {
    console.log('Not a pull request or pull request comment. Skipping.');
    return;
  }

  console.log(`Processing event "${eventName}" for PR #${prNumber}`);

  // 1. Ingestion
  if (eventName === 'pull_request' && (context.payload.action === 'opened' || context.payload.action === 'ready_for_review')) {
    console.log('Triggering PR Ingestion: adding status:needs-triage');
    await github.rest.issues.addLabels({
      owner,
      repo,
      issue_number: prNumber,
      labels: ['status:needs-triage']
    });
  }

  // 2. Triage (Manual area:* or devops label added)
  if (eventName === 'pull_request' && context.payload.action === 'labeled') {
    const labelAdded = context.payload.label.name;
    console.log(`Label added: ${labelAdded}`);
    if (labelAdded.startsWith('area:') || labelAdded === 'devops') {
      console.log('Area or devops label detected. Applying status:under-review and removing status:needs-triage');
      await github.rest.issues.addLabels({
        owner,
        repo,
        issue_number: prNumber,
        labels: ['status:under-review']
      });
      try {
        await github.rest.issues.removeLabel({
          owner,
          repo,
          issue_number: prNumber,
          name: 'status:needs-triage'
        });
      } catch {
        console.log('status:needs-triage label was not present');
      }
    }

    // 3. Feedback Loop - Blocked
    if (labelAdded === 'blocked') {
      console.log('Blocked label detected. Removing status:under-review');
      try {
        await github.rest.issues.removeLabel({
          owner,
          repo,
          issue_number: prNumber,
          name: 'status:under-review'
        });
      } catch {
        console.log('status:under-review label was not present');
      }
    }
  }

  // 4. Feedback Loop - Resume
  if (eventName === 'pull_request' && context.payload.action === 'synchronize') {
    console.log('PR synchronized (new commit pushed). Checking if currently blocked.');
    const { data: pr } = await github.rest.pulls.get({
      owner,
      repo,
      pull_number: prNumber
    });
    const labels = pr.labels.map(l => l.name);
    if (labels.includes('blocked')) {
      console.log('PR is blocked. Removing blocked label and re-applying status:under-review');
      await github.rest.issues.addLabels({
        owner,
        repo,
        issue_number: prNumber,
        labels: ['status:under-review']
      });
      try {
        await github.rest.issues.removeLabel({
          owner,
          repo,
          issue_number: prNumber,
          name: 'blocked'
        });
      } catch {
        console.log('blocked label was not present');
      }
    }
  }
}
