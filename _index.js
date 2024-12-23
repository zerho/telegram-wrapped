const puppeteer = require('puppeteer');

const PP_URL = 'file:///Users/matteototo/spaces/misc/Telegram%20Desktop/DataExport_2024-12-09/chats/chat_003/messages.html';
const BUG_URL = 'file:///Users/matteototo/spaces/misc/Telegram%20Desktop/DataExport_2024-12-09/chats/chat_008/messages.html';
let TEST_URL = BUG_URL;

(async () => { 
	const browser = await puppeteer.launch(); 
	const page = await browser.newPage(); 
	await page.goto(TEST_URL); 
 
	const chatTitleSelector = '.page_header .text.bold'; 
	await page.waitForSelector(chatTitleSelector); 
	const titles = await page.$$eval( 
		chatTitleSelector, 
		titles => titles.map(title => title.innerText) 
	); 
	console.log('Titolo: ', titles); 

    const memberNameSelector = '.message .body .from_name';
    await page.waitForSelector(chatTitleSelector); 
	const memberNames = await page.$$eval( 
		memberNameSelector, 
		memberNames => memberNames.map(memberName => memberName.innerText) 
	); 

    const map = memberNames.reduce((acc, e) => acc.set(e, (acc.get(e) || 0) + 1), new Map());
    // console.log(map.keys());
    // console.log(map.values());
    // console.log(map.entries());

    for (let [key, value] of map.entries()) {
        console.log(key + " wrote " + value + " times");
    }

	await browser.close(); 
})();
