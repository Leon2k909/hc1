async page => {
  const reports = [];
  for (const state of ['index','search','empty']) {
    await page.goto(`http://127.0.0.1:8766/output/playwright/career-record/${state}.html`);
    for (const width of [1920,1280,960,720]) {
      await page.setViewportSize({ width, height:1080 });
      await page.evaluate(() => document.fonts.ready);
      const result = await page.evaluate(() => {
        const record = document.querySelector('.weapon-record').getBoundingClientRect();
        const issues = [];
        for (const control of document.querySelectorAll('.weapon-category,.weapon-search,.weapon-sort-option,.weapon-clear,.weapon-record-empty')) {
          const box = control.getBoundingClientRect();
          if (box.left < record.left - 1 || box.right > record.right + 1) issues.push(control.className + ' outside record');
          if (control.scrollWidth > control.clientWidth + 1) issues.push(control.className + ' text overflow');
        }
        return { viewport:innerWidth, recordWidth:Math.round(record.width), categories:document.querySelectorAll('.weapon-category').length, issues };
      });
      reports.push({state,...result});
      await page.screenshot({path:`output/playwright/career-record/${state}-${width}.png`});
      if (result.issues.length) throw new Error(JSON.stringify(reports));
    }
  }
  console.log(JSON.stringify(reports));
}
