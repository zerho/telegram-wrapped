#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const csv = require('csv-stringify');

function normalizeLines(content) {
    const lines = content.split('\n');
    const normalizedMessages = [];
    let currentMessage = '';

    for (const line of lines) {
        if (line.trim() === '') continue;
        
        if (line.startsWith('[')) {
            if (currentMessage) {
                normalizedMessages.push(currentMessage);
            }
            currentMessage = line;
        } else {
            currentMessage += ' ' + line.trim();
        }
    }
    
    // Don't forget the last message
    if (currentMessage) {
        normalizedMessages.push(currentMessage);
    }

    return normalizedMessages;
}

function parseMessage(line) {
    const dateMatch = line.match(/^\[(.*?)\]/);
    if (!dateMatch) return null;

    const date = dateMatch[1];
    const remainingText = line.slice(dateMatch[0].length).trim();
    
    const senderMatch = remainingText.match(/(.*?):/);
    if (!senderMatch) return null;

    const sender = senderMatch[1].trim();
    const text = remainingText.slice(senderMatch[0].length).trim();

    return {
        date,
        sender,
        text
    };
}

async function convertTxtToCSV(inputFile) {
    // Read the input file
    const content = fs.readFileSync(inputFile, 'utf-8');
    
    // Normalize messages
    const normalizedLines = normalizeLines(content);
    
    // Parse messages
    const messages = normalizedLines
        .map(line => parseMessage(line))
        .filter(msg => msg !== null);

    // Generate output filename based on input filename
    const outputFile = path.join(
        path.dirname(inputFile),
        `${path.basename(inputFile, '.txt')}_converted.csv`
    );

    // Create CSV write stream
    const writableStream = fs.createWriteStream(outputFile);
    
    // Configure CSV stringifier with proper escaping
    const stringifier = csv.stringify({
        header: true,
        columns: [
            { key: 'date', header: 'date' },
            { key: 'sender', header: 'sender' },
            { key: 'text', header: 'text' }
        ],
        quoted: true,      // Quote all fields
        quote: '"',        // Use double quotes
        escape: '"',       // Escape quotes with double quotes
        record_delimiter: 'windows'  // Use CRLF for better compatibility
    });
    
    // Pipe the stringifier to the write stream
    stringifier.pipe(writableStream);
    
    // Write all messages
    messages.forEach(message => stringifier.write(message));
    
    // End the stringifier
    stringifier.end();
    
    return new Promise((resolve, reject) => {
        writableStream.on('finish', () => resolve(outputFile));
        writableStream.on('error', reject);
    });
}

// CLI handling
async function main() {
    // Check if input file is provided
    if (process.argv.length < 3) {
        console.error('Please provide an input file path.');
        console.error('Usage: whatsapp-to-csv <input-file>');
        process.exit(1);
    }

    const inputFile = process.argv[2];

    // Check if file exists
    if (!fs.existsSync(inputFile)) {
        console.error(`Error: File '${inputFile}' does not exist.`);
        process.exit(1);
    }

    try {
        const outputFile = await convertTxtToCSV(inputFile);
        console.log(`Conversion completed successfully!\nOutput saved to: ${outputFile}`);
        console.warn(`BE AWARE that the file generated has still an issue with messages containing new lines, you'll have to remove them manually with search and replace`);
    } catch (error) {
        console.error('Error during conversion:', error);
        process.exit(1);
    }
}

// Only run main if script is called directly (not imported)
if (require.main === module) {
    main();
}

// Export for potential module usage
module.exports = convertTxtToCSV;