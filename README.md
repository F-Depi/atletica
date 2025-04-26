# Initialization
Questo sito utilizza un database di dati che ho creato e continuo ad aggiornare
con quest'altro progetto:
[database-atletica-italiana](https://github.com/F-Depi/database-atletica-italiana)

Il database ha la seguente struttura.

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

## TO DO
 - Creare una pagina con le statistiche attualmente contenute 
 [qui](https://github.com/F-Depi/database-atletica-italiana/tree/main/statistiche)
 - Aggiungere una sezione per fare query direttamente sul database
 - Aggiungere i risultati all time riportati sul
 [sito fidal](https://www.fidal.it/content/Statistiche/25404)
 - Aggiungere i risultati delle gare in diretta. Ho già contruito il
 [programma](https://github.com/F-Depi/stats-athletic/tree/main/database_new),
 ma devo renderlo più accurato.
