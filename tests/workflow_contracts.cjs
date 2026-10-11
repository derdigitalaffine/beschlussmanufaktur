const fs = require('node:fs');
const assert = require('node:assert/strict');

function extractGithubScript(path) {
  const lines = fs.readFileSync(path, 'utf8').split('\n');
  const marker = lines.findIndex((line) => line.trim() === 'script: |');
  assert.notEqual(marker, -1, `${path}: github-script block missing`);

  const script = [];
  for (const line of lines.slice(marker + 1)) {
    if (line.startsWith('            ')) {
      script.push(line.slice(12));
      continue;
    }
    if (line.trim() === '') {
      script.push('');
      continue;
    }
    break;
  }
  assert.ok(script.length, `${path}: github-script block empty`);
  return script.join('\n');
}

async function runWorkflow(path, fixture) {
  const script = extractGithubScript(path);
  const writes = [];

  const endpoints = {
    issuesListForRepo: Symbol('issues.listForRepo'),
    issuesListComments: Symbol('issues.listComments'),
    pullsList: Symbol('pulls.list'),
    pullsListFiles: Symbol('pulls.listFiles'),
  };

  const github = {
    rest: {
      issues: {
        listForRepo: endpoints.issuesListForRepo,
        listComments: endpoints.issuesListComments,
        updateComment: async (args) => writes.push({ type: 'update', ...args }),
        createComment: async (args) => writes.push({ type: 'create', ...args }),
      },
      pulls: {
        list: endpoints.pullsList,
        listFiles: endpoints.pullsListFiles,
      },
    },
    paginate: async (endpoint, args) => {
      if (endpoint === endpoints.issuesListForRepo) return fixture.issues || [];
      if (endpoint === endpoints.pullsList) return fixture.pulls || [];
      if (endpoint === endpoints.pullsListFiles) return fixture.prFiles?.[args.pull_number] || [];
      if (endpoint === endpoints.issuesListComments) return fixture.comments?.[args.issue_number] || [];
      throw new Error(`Unexpected paginate endpoint in ${path}`);
    },
  };

  const context = {
    repo: { owner: 'example', repo: 'beschlussmanufaktur' },
    eventName: 'workflow_dispatch',
    payload: {},
  };
  const core = { info: () => {} };

  const execute = new Function(
    'github',
    'context',
    'core',
    `return (async () => {\n${script}\n})();`,
  );
  await execute(github, context, core);
  return writes;
}

async function testCoordinationWorkflow() {
  const issue = {
    number: 52,
    title: 'Contract hardening',
    html_url: 'https://example.invalid/issues/52',
    updated_at: '2026-10-11T12:00:00Z',
  };
  const olderClaim = {
    body: '<!-- coordination:claim:v2 -->\n- Phase: discovery\n- Branch: none\n- Coordination keys: workflow:legacy',
    author_association: 'OWNER',
    created_at: '2026-10-11T08:00:00Z',
    updated_at: '2026-10-11T08:00:00Z',
  };
  const canonicalClaim = {
    body: '<!-- coordination:claim:v2 -->\n- Phase: implementation\n- Branch: agent/contracts-workflow-hardening-52\n- Coordination keys: workflow:agent-coordination',
    author_association: 'OWNER',
    created_at: '2026-10-11T10:00:00Z',
    updated_at: '2026-10-11T12:00:00Z',
  };
  const terminalHandoff = {
    body: '<!-- coordination:handoff:v2 -->\n- Disposition: completed',
    author_association: 'OWNER',
    created_at: '2026-10-11T11:00:00Z',
    updated_at: '2026-10-11T11:00:00Z',
  };

  const writes = await runWorkflow('.github/workflows/coordination-dashboard.yml', {
    issues: [issue],
    pulls: [],
    comments: {
      52: [olderClaim, canonicalClaim, terminalHandoff],
      38: [],
    },
  });

  assert.equal(writes.length, 1);
  const body = writes[0].body;
  assert.match(body, /#52/);
  assert.match(body, /\| implementation \|/);
  assert.match(body, /Mehrere kanonische Claim-Kommentare/);
  assert.doesNotMatch(body, /Keine aktiven Claims/);
}

async function testRoadmapWorkflow() {
  const validIssue = {
    number: 43,
    title: 'Valid roadmap item',
    html_url: 'https://example.invalid/issues/43',
    author_association: 'OWNER',
    body: `<!-- roadmap:item:v1 -->
- Stream: ux
- Outcome: Nutzerfluss ist messbar konsistent.
- Horizon: now
- Priority: P1
- Status: discovery
- Risk: high
- Quality gates: G0, G1
- Depends on: none
- Blocks: none
- Coordination keys: ui:navigation
- Council required: yes
- Decision questions: Welche Interaktion reduziert Fehler?
- Evidence: none yet
- Last reviewed: 2026-10-11`,
  };
  const invalidIssue = {
    number: 99,
    title: 'Invalid roadmap item',
    html_url: 'https://example.invalid/issues/99',
    author_association: 'OWNER',
    body: `<!-- roadmap:item:v1 -->
- Stream: ux
- Outcome: Ungültiger Vertrag muss sichtbar werden.
- Horizon: next
- Priority: P2
- Status: ready
- Risk: medium
- Quality gates: G0,G2
- Depends on: none
- Blocks: none
- Coordination keys: ui:test
- Council required: no
- Decision questions: none
- Evidence: none yet
- Last reviewed: 2026-02-31`,
  };

  const writes = await runWorkflow('.github/workflows/roadmap-dashboard.yml', {
    issues: [validIssue, invalidIssue],
    comments: { 41: [] },
  });

  assert.equal(writes.length, 1);
  const body = writes[0].body;
  assert.match(body, /Ungültige Metadaten: \*\*1\*\*/);
  assert.match(body, /Roadmap-Metadaten unvollständig\/ungültig: #99/);
  assert.match(body, /`G0,G1`/);
}

(async () => {
  await testCoordinationWorkflow();
  await testRoadmapWorkflow();
  console.log('workflow contract tests passed');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
