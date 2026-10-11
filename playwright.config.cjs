const {defineConfig}=require("@playwright/test");
module.exports=defineConfig({
  testDir:"tests/browser",timeout:60000,workers:1,
  use:{baseURL:"http://127.0.0.1:8768",viewport:{width:1440,height:1000},screenshot:"only-on-failure"},
  webServer:{command:"node scripts/serve.cjs 8768",url:"http://127.0.0.1:8768/research.html",reuseExistingServer:false},
  reporter:[["list"],["html",{open:"never"}]],
});
