# Initialization
Il database dei dati è create e aggiornato da 
[database-atletica-italiana](https://github.com/F-Depi/database-atletica-italiana)


La prima volta che si runna il sito:

```
export FLASK_APP=app.py                                                                                                                                                     <<<
export FLASK_ENV=development
flask run
```

Poi:
```
flask run
```

## Struttura del database postgreSQL
 - id SERIAL PRIMARY KEY,
 - prestazione FLOAT,
 - vento VARCHAR(10),
 - tempo VARCHAR(20),
 - cronometraggio VARCHAR(20),
 - atleta VARCHAR(100),
 - anno VARCHAR(4),
 - categoria VARCHAR(20),
 - società VARCHAR(100),
 - posizione VARCHAR(10),
 - luogo VARCHAR(100),
 - data DATE,
 - link_atleta VARCHAR(200),
 - link_societa VARCHAR(200),
 - disciplina VARCHAR(50),
 - ambiente CHAR(1)


_Un grazie all'IA, che dopo 2 anni che volevo fare un sito, ma non avevo il
tempo di imparare mi ha permesso di imbastire questo progetto_

## Pompt (Sonnet 3.5):
I'm use fedora linux and I want to selfhost a website.

Take into considerations the athletic disciplines listed in this json file

dizionatio_gare.json
{
"50m": {
"codice": "56",
"tipo": "Corse Piane",
"classifica": "tempo",
"vento": "sì"
},
"60m": {
"codice": "01",
"tipo": "Corse Piane",
"classifica": "tempo",
"vento": "sì"
},
"80m": {
"codice": "02",
"tipo": "Corse Piane",
"classifica": "tempo",
"vento": "sì"
},
"alto": {
"codice": "26",
"tipo": "Salti",
"classifica": "distanza",
"vento": "no"
},
"asta": {
"codice": "27",
"tipo": "Salti",
"classifica": "distanza",
"vento": "no"
},
"lungo": {
"codice": "28",
"tipo": "Salti",
"classifica": "distanza",
"vento": "sì"
},
"triplo": {
"codice": "29",
"tipo": "Salti",
"classifica": "distanza",
"vento": "sì"
},
"60Hs_h106-9.14": {
"codice": "HB",
"tipo": "Corse Piane",
"tipo": "Ostacoli",
"classifica": "tempo",
"vento": "sì",
"categoria": "PM SM"
},
"60Hs_h84-8.50": {
"codice": "HF",
"tipo": "Corse Piane",
"tipo": "Ostacoli",
"classifica": "tempo",
"vento": "sì",
"categoria": "CM JF PF SF SF35"
}
}

I have the results saved in database of csv files. Each csv file contains more than 100k rows. It's sufficient to call the python function get_file_database(ambiente, gara) where 'ambiente' is 'I' for indoor or 'P' for outdoor and 'gara' is one of the keys of the json file to get a dataframe with columns specified here

colonne_dtype.json
{
"prestazione": "float",
"vento": "string",
"tempo": "string",
"cronometraggio": "string",
"atleta": "string",
"anno": "string",
"categoria": "string",
"società": "string",
"posizione": "string",
"luogo": "string",
"data": "string",
"link_atleta": "string",
"link_società": "string"
}

I need to build a website I'm going to selfhost, where people can look at rankings and statistic made from my database. (some thing like this https://worldathletics.org/records/toplists).
I have no experience in web developement, I only known python.
My only requirements are that the website needs to be super fast and simple.
Start by addressing the creation of a posgress database for maximum performance.
Write down the project structure and the content of each file.
The task you are about to complete is essential for these results to be seen by the public.
Keep the project as simple as possible, minimizing the number of files
