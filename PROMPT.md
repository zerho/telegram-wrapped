# PROMPT

## prompt usato per creare l'utils su cui si baserà il progetto

// partendo da un file di esempio
Usa ancora l'allegato di prima.
Comportati come un software engineer senior ma che scrive codice semplice e leggibile.
Come puoi notare è un export di una chat di telegram rappresentato in HTML,  nella pagina ci sono 32 messaggi, li riconosci perché sono sempre dei div con classe "message".

Mi serve uno script che iteri messaggio per messaggio e crei un CSV con delle informazioni astratte, ora ti spiego cosa astrarre.

Questa dev'essere l'intestazione del CSV:
id, timestamp, sender, text, replyToId;

Inizia ad iterare i messaggi grazie alla classe "message default clearfix",
l'id di questo div mettilo nella colonna id del csv.
L'innerText del div con classe ".message .body .from_name" mettilo nel sender, se non c'è usa lo stesso sender del div precedente.
Il Title del div ".pull_right.date.details" mettilo in timestamp.
L'innerText del div ".message .body .text" mettilo in text.
Se c'è un div ".reply_to.details" allora prendi l'href del tag a figlio e mettilo in replyToId.

Scrivi tutto in javascript per nodeJS.
Alla fine dell'esecuzione il script scrive un file in locale.
Mi raccomando con l'escape dei campi per non rompere il csv.
grazie.
