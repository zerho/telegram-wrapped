const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

// Utility function to escape CSV fields
function escapeCsvField(field) {
    if (!field) return '';
    if (field.includes(',') || field.includes('\n') || field.includes('"')) {
        return `"${field.replace(/"/g, '""')}"`;
    }
    return field;
}

// Function to convert messages to CSV lines
function messagesToCsvLines(messages) {
    return messages.map(message => {
        const csvLine = [
            escapeCsvField(message.id),
            escapeCsvField(message.timestamp),
            escapeCsvField(message.sender),
            escapeCsvField(message.text),
            escapeCsvField(message.replyToId)
        ].join(',');
        return csvLine;
    }).join('\n');
}

async function parseChatFile(page, filePath) {
    // Load the HTML file
    const fileUrl = `file://${filePath}`;
    await page.goto(fileUrl, { waitUntil: 'networkidle0' });

    // Extract messages data
    const messages = await page.evaluate(() => {
        let lastSender = '';
        const messageElements = document.querySelectorAll('.message.default.clearfix');
        
        return Array.from(messageElements).map(element => {
            const id = element.id?.replace('message', '') || '';
            const timestampElement = element.querySelector('.pull_right.date.details');
            const timestamp = timestampElement?.getAttribute('title') || '';
            
            const senderElement = element.querySelector('.body .from_name');
            const sender = senderElement 
                ? senderElement.textContent.trim() 
                : lastSender;
            lastSender = sender || lastSender;

            const textElement = element.querySelector('.body .text');
            const text = textElement?.textContent.trim() || '';

            const replyElement = element.querySelector('.reply_to.details a');
            const replyToId = replyElement 
                ? (replyElement.getAttribute('href') || '').replace('#go_to_message', '')
                : '';

            return { id, timestamp, sender, text, replyToId };
        });
    });

    return messages;
}

async function processAllChats(inputFolder) {
    const browser = await puppeteer.launch({
        headless: "new"
    });

    try {
        const page = await browser.newPage();
        let allMessages = [];
        
        // Get all HTML files in the folder
        const files = fs.readdirSync(inputFolder)
            .filter(file => file.toLowerCase().endsWith('.html'))
            .sort(); // Sort to process in order (messages.html, messages2.html, etc.)

        console.log(`Found ${files.length} HTML files to process`);

        // Process each file
        for (const file of files) {
            const filePath = path.join(inputFolder, file);
            
            try {
                console.log(`Processing ${file}...`);
                const messages = await parseChatFile(page, filePath);
                allMessages = allMessages.concat(messages);
                console.log(`Successfully processed ${file} - ${messages.length} messages extracted`);
            } catch (error) {
                console.error(`Error processing ${file}:`, error);
                console.error('Stopping processing at this file.');
                throw new Error(`Failed at file: ${file}`);
            }
        }

        // Create CSV content
        const csvHeader = 'id,timestamp,sender,text,replyToId\n';
        const csvContent = csvHeader + messagesToCsvLines(allMessages);

        // Write final CSV file
        const outputPath = path.join(process.cwd(), '/exports/all_messages.csv');
        await fs.promises.writeFile(outputPath, csvContent);
        
        console.log(`CSV file created successfully with ${allMessages.length} total messages!`);
        console.log(`Output saved to: ${outputPath}`);

    } catch (error) {
        console.error('Error during processing:', error);
    } finally {
        await browser.close();
    }
}

// Get input folder from command line argument or use default
const inputFolder = process.argv[2] || './chats';

// Ensure input folder exists
if (!fs.existsSync(inputFolder)) {
    console.error(`Input folder does not exist: ${inputFolder}`);
    process.exit(1);
}

// Run the script
processAllChats(inputFolder).catch(console.error);