#!/usr/bin/env node
/**
 * Passive and safe public deployment smoke check.
 * Only performs HTTP GET against public URLs; never submits forms or changes databases.
 */
'use strict';
import assert from 'node:assert/strict';

const checks = [
  {
    title: 'Apex website TEC EPR product page',
    url: 'https://thuemancokelimited.com/software.html',
    test: (data, response) => {
      assert.equal(response.status, 200, 'Expected 200');
      assert.match(data, /TEC EPR Clinic Edition/, 'Product identity missing');
      assert.match(data, /api\/contact/, 'Existing business CRM enquiry flow not available in HTML');
      assert.doesNotMatch(data, /\.tar\.gz|private\.pem/i, 'Unexpected distribution master/key reference');
    }
  },
  {
    title: 'WWW TEC EPR product page',
    url: 'https://www.thuemancokelimited.com/software.html',
    test: (data, response) => {
      assert.equal(response.status, 200, 'Expected 200');
      assert.match(data, /TEC EPR Clinic Edition/, 'Product identity missing');
    }
  },
  {
    title: 'Existing privacy policy and consent notice',
    url: 'https://thuemancokelimited.com/privacy.html',
    test: (data, response) => {
      assert.equal(response.status, 200, 'Expected 200');
      assert.match(data, /Privacy Notice|Privacy notice/i);
      assert.match(data, /TEC EPR software enquiries/i);
    }
  },
  {
    title: 'Existing CRM front end retained',
    url: 'https://thuemancokelimited.com/crm.html',
    test: (data, response) => {
      assert.equal(response.status, 200, 'Expected CRM static UI available');
      assert.match(data, /<html|<title/i);
    }
  },
  {
    title: 'Railway backend health',
    url: 'https://api.thuemancokelimited.com/api/health',
    test: (data, response) => {
      assert.equal(response.status, 200, 'Expected backend health 200');
      const json = JSON.parse(data);
      assert.equal(json.ok, true, 'API reports unhealthy');
    }
  }
];

async function run() {
  let failures = 0;
  for (const check of checks) {
    try {
      const response = await fetch(check.url, {
        method: 'GET',
        redirect: 'follow',
        signal: AbortSignal.timeout(15000),
        headers: { 'Accept': 'text/html,application/json', 'User-Agent': 'TCL-Release-Availability/1.0' }
      });
      const text = await response.text();
      check.test(text, response);
      console.log('[PASS]', check.title, 'HTTP', response.status, new URL(response.url).hostname);
    } catch (e) {
      failures += 1;
      console.error('[FAIL]', check.title, '-', e.message);
    }
  }
  console.log('Checks:', checks.length, 'Failures:', failures);
  if (failures) process.exitCode = 1;
}
run().catch(e => { console.error('Smoke failed:',e.message);process.exitCode=1; });
