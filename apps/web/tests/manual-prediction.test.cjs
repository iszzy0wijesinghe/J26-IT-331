const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

// Compile the actual component in memory; no additional test dependencies.
const filename = path.resolve(__dirname, '../src/features/c4/components/ManualPredictionResult.tsx');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS },
}).outputText;
const loaded = new Module(filename, module);
loaded.filename = filename;
loaded.paths = module.paths;
loaded._compile(compiled, filename);
const Result = loaded.exports.default;

for (const label of ['Trusted', 'Suspicious', 'Untrusted']) {
  test(`renders ${label} and its score independently of health warnings`, () => {
    const result = { label, score: 0.61, warnings: ['Battery voltage is zero or negative.', 'Device reports a sensor fault.', 'Telemetry is stale.'], assumptions: { rx_delay_s: 'Assumed 5 seconds' } };
    const html = renderToStaticMarkup(React.createElement(Result, { result }));
    assert.ok(html.includes(`Predicted Label: <strong>${label}</strong>`));
    assert.ok(html.includes('<strong>0.6100</strong>'));
    assert.ok(html.includes(`Model class: ${label}.`));
    assert.ok(html.includes('Input-health warning (separate from model prediction)'));
    for (const warning of result.warnings) assert.ok(html.includes(warning));
    assert.ok(!html.includes('with normal behavior'));
    assert.ok(html.includes('Assumed 5 seconds'));
  });
}

test('healthy inputs show the prediction without a health alert', () => {
  const html = renderToStaticMarkup(React.createElement(Result, { result: { label: 'Example model label', score: 0.123456, warnings: [], assumptions: {} } }));
  assert.ok(html.includes('Example model label'));
  assert.ok(html.includes('0.1235'));
  assert.ok(!html.includes('role="alert"'));
});
