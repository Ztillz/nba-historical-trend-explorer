const {test,expect}=require("@playwright/test");

test("default research, metric selection, evidence and exports",async({page},testInfo)=>{
  const errors=[];page.on("pageerror",error=>errors.push(error.message));
  await page.goto("/research.html");
  await expect(page.locator("#researchStatus")).toContainText("Experiment ready.");
  await expect(page.locator("#researchCards")).toContainText("1,205");
  await expect(page.locator("#researchCards")).toContainText("0.360");
  await expect(page.locator("#scatterPlot circle")).toHaveCount(1205);
  await expect(page.locator("#benchmarkVerdict")).toContainText("mean absolute error");
  await page.screenshot({path:testInfo.outputPath("research-desktop.png"),fullPage:true});
  await page.getByRole("button",{name:"Assist differential",exact:true}).click();
  await expect(page.locator("#plotTitle")).toHaveText("Assist differential");
  await expect(page.locator("#researchCards")).toContainText("0.506");
  await page.getByLabel("Find a team or season").fill("Celtics");
  await expect(page.getByRole("button",{name:"Boston Celtics",exact:true}).first()).toBeVisible();
  await page.getByRole("button",{name:"Boston Celtics",exact:true}).first().click();
  await expect(page.locator("#selectedTeam")).toContainText("Boston Celtics");
  await expect(page.locator("#selectedTeam")).toContainText("Outcome:");
  const csv=page.waitForEvent("download");await page.getByRole("button",{name:"Download evidence CSV"}).click();
  const downloaded=await csv;expect(downloaded.suggestedFilename()).toContain("assist_diff.csv");
  await downloaded.saveAs(testInfo.outputPath("evidence.csv"));
  const json=page.waitForEvent("download");await page.getByRole("button",{name:"Download analysis JSON"}).click();
  expect((await json).suggestedFilename()).toBe("nba-research-analysis.json");
  const link=page.url();await page.goto(link);
  await expect(page.locator("#researchStatus")).toContainText("Experiment ready.");
  await expect(page.locator("#plotTitle")).toHaveText("Assist differential");
  expect(errors).toEqual([]);
});

test("alternate experiment and validation feedback",async({page})=>{
  await page.goto("/research.html");await expect(page.locator("#researchStatus")).toContainText("Experiment ready.");
  await page.getByLabel("Observe first",{exact:true}).selectOption("10");
  await page.getByLabel("Measure afterward").selectOption("next_10");
  await page.getByLabel("Later performance").selectOption("future_point_diff");
  await page.getByRole("button",{name:"Explore findings"}).click();
  await expect(page.locator("#researchStatus")).toContainText("Experiment ready.");
  await expect(page.locator("#plotUnits")).toContainText("First 10");
  await expect(page.locator("#benchmarkBars")).toContainText("points/game");
  await page.getByLabel("Starting season",{exact:true}).selectOption("2025-26");
  await page.getByLabel("Ending season",{exact:true}).selectOption("1983-84");
  await page.getByRole("button",{name:"Explore findings"}).click();
  await expect(page.getByRole("alert")).toContainText("Starting season must precede ending season");
});

test("historical queries and methods navigation",async({page})=>{
  await page.goto("/");await expect(page.locator("#dataStatus")).toContainText("loaded");
  await page.getByRole("button",{name:"Run historical query"}).click();
  await expect(page.locator("#summaryCards")).toContainText("1,205");
  await expect(page.locator("#coverageMessage")).toContainText("18 of 1,223");
  await page.getByRole("link",{name:"Methods & guide",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Explore with context.",exact:true})).toBeVisible();
});

test("mobile layout has no page-wide horizontal overflow",async({page},testInfo)=>{
  await page.setViewportSize({width:390,height:844});await page.goto("/research.html");
  await expect(page.locator("#researchStatus")).toContainText("Experiment ready.");
  const width=await page.evaluate(()=>({page:document.documentElement.scrollWidth,viewport:window.innerWidth}));
  expect(width.page).toBeLessThanOrEqual(width.viewport);
  await page.screenshot({path:testInfo.outputPath("research-mobile.png"),fullPage:true});
});
