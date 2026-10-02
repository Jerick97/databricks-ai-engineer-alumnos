// Inspección del HTML obtenido por HTTP autenticado; no representa login SSO en navegador.
const {chromium}=require('/Users/macdenix/clawd/node_modules/playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
(async()=>{const root=path.resolve(__dirname,'..');const source=path.join(root,'reports/lab-app-observed.html');
const browser=await chromium.launch({channel:'chrome',headless:true});const checks=[];
for(const width of [1280,390]){const page=await browser.newPage({viewport:{width,height:900}});await page.goto('file://'+source);
const state=await page.evaluate(()=>({hasForm:!!document.querySelector('form'),hasAnswer:document.querySelector('pre')?.textContent.includes('116024.88'),overflow:document.documentElement.scrollWidth>innerWidth+1}));
await page.screenshot({path:path.join(root,'reports',`app-${width}.png`),fullPage:true});checks.push({width,...state});await page.close();}
await browser.close();const report={scope:'Offline rendering of authenticated HTTP response; no browser SSO claim',html_sha256:crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex'),checks,pass:checks.every(x=>x.hasForm&&x.hasAnswer&&!x.overflow)};fs.writeFileSync(path.join(root,'reports/app-visual.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!report.pass)process.exitCode=1;})();
