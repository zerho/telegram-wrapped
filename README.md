# Telegram Wrapped

## Folder Structure

example absolute path `file:///Users/matteototo/spaces/misc/Telegram_DataExport_2024-12-09/chats/chat_003/messages.html`

`lists/chats.html`      list of all chats  
`chats/chat_[number]/`  folder that contains everything about the chat
`chats/chat_[number]/messages[number].html` files that contains the chat, incrementally.  

## Hacking/Debugging

per capire la struttura della chat è comodo applicare uno stile su tutti i messaggi simili per esempio così
`document.querySelectorAll('.message.default').forEach(e => e.style.border = '2px solid red');`  

`.page_header .text.bold`   Titolo chat
`.message.service .body`    Messaggi di servizio come ingresso in chat, giorno della settimana, e cambio foto
`.message .body .from_name` Nome del sender
`.message .body .text`      Testo del messaggio
`.pull_right.date.details`  Timestamp messaggio
`.reply_to.details`         ID del messaggio di Reply
`.media_wrap`               Generic Media Wrapper (da controllare meglio)

## Ipotesi struttura DB

Probabilmente non ha senso continuare a fare script che pescano sempre dal dataset raw che è in HTML.
Prendendo spunto dall'export di Whatsapp avrebbe senso fare un unico script che converte da html a CSV,
strutturerei il dato così:

Timestamp,                          Sender, Message,        MessageId,  ReplyToId,  Media?
26.07.2021 11:06:16 UTC+01:00",     Matteo, "Ciao tutti",   0000001,    null,       null
26.07.2021 12:00:00 UTC+01:00",     Gino,   "Ciao Matteo",  0000002,    0000001,    null

## TODO

- i media non sono gestiti
- quando i replyTo si riferiscono ad un'altra pagine si salva un ID sporco con una stringa in più
- decidere se tracciare i service messages o altro.
- [WA] `wa_convert.js` ha ancora un problema, non riesce ad accorpare il testo dei messaggi che vanno a capo con il proprio messaggio padre

## DATA EXPLORATION

sto studiando questa guida
<https://www.youtube.com/watch?v=QgfkY_M6IEQ&ab_channel=JohanGodinho>

