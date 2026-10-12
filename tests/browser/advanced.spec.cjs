const {test,expect}=require('@playwright/test');

test('advanced questions, persistence, evidence, exports and bookmarks',async({page},testInfo)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/advanced.html');await expect(page.locator('#advancedStatus')).toContainText('Advanced experiment ready.');
 await expect(page.locator('#advancedCards')).toContainText('510');await expect(page.locator('#advancedCards')).toContainText('360');
 await expect(page.locator('#advancedCards')).toContainText('0.109');await expect(page.locator('#advancedScatter circle')).toHaveCount(510);
 await expect(page.locator('#advancedVerdict')).toContainText('10 of 12');await expect(page.locator('#advancedCoverage')).toContainText('40,696');
 await page.screenshot({path:testInfo.outputPath('advanced-desktop.png'),fullPage:true});
 await page.getByRole('button',{name:'Pace',exact:true}).click();
 await expect(page.getByLabel('Later characteristic',{exact:true})).toHaveValue('pace');
 await expect(page.locator('#advancedAssociation')).toContainText('0.888');
 await page.getByLabel('Research question',{exact:true}).selectOption('passing_offense');
 await expect(page.locator('#advancedAblation')).toContainText('alone changes MAE');
 await page.getByLabel('Find a team or season',{exact:true}).fill('Celtics');
 await page.getByRole('button',{name:'Boston Celtics',exact:true}).first().click();
 await expect(page.locator('#advancedTeam')).toContainText('Outcome:');
 const csv=page.waitForEvent('download');await page.getByRole('button',{name:'Download advanced evidence CSV',exact:true}).click();
 const file=await csv;expect(await file.suggestedFilename()).toBe('nba-advanced-evidence.csv');await file.saveAs(testInfo.outputPath('advanced-evidence.csv'));
 const json=page.waitForEvent('download');await page.getByRole('button',{name:'Download advanced analysis JSON',exact:true}).click();expect((await json).suggestedFilename()).toBe('nba-advanced-analysis.json');
 await page.getByLabel('Observe first',{exact:true}).selectOption('30');await page.getByLabel('Measure afterward',{exact:true}).selectOption('remaining');
 await page.getByLabel('Early characteristic',{exact:true}).selectOption('delta_tov_rate');await page.getByLabel('Later characteristic',{exact:true}).selectOption('pace');
 const link=page.url();await page.goto(link);await expect(page.locator('#advancedStatus')).toContainText('Advanced experiment ready.');
 await expect(page.getByLabel('Observe first',{exact:true})).toHaveValue('30');await expect(page.getByLabel('Early characteristic',{exact:true})).toHaveValue('delta_tov_rate');await expect(page.getByLabel('Later characteristic',{exact:true})).toHaveValue('pace');
 expect(errors).toEqual([]);
});

test('advanced mobile layout and navigation',async({page},testInfo)=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/advanced.html');
 await expect(page.locator('#advancedStatus')).toContainText('Advanced experiment ready.');
 const width=await page.evaluate(()=>({page:document.documentElement.scrollWidth,viewport:window.innerWidth}));expect(width.page).toBeLessThanOrEqual(width.viewport);
 await page.screenshot({path:testInfo.outputPath('advanced-mobile.png'),fullPage:true});
 await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Methods & guide',exact:true}).click();await expect(page.getByRole('heading',{name:'Advanced efficiency and style research',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Advanced research',exact:true}).click();await expect(page.locator('#advancedStatus')).toContainText('Advanced experiment ready.');
});
