### Dataset: 
https://offeneregister.de/


### Data- Tables: 
Available tables: 
- company
- name
- officer
- registrations

I retrieved the included tables and columns via: 
```sql
SELECT m.name as tableName, 
       p.name as columnName, 
       p.type as columnType FROM sqlite_master m 
LEFT OUTER JOIN 
       pragma_table_info(m.name) p 
       ON m.name <> p.name 
       WHERE m.type IN ('table', 'view') 
       AND m.name NOT LIKE 'sqlite_%' 
       ORDER BY tableName, columnName;
```


As we are interested in ER/NLP I filtered this list for non-structural, TEXT/CLOB columns only via:

```sql
SELECT * FROM (SELECT  
    m.name as tableName,  
    p.name as columnName,  
    p.type as columnType  
FROM  
    sqlite_master m  
LEFT OUTER JOIN  
    pragma_table_info(m.name) p  
ON  
    m.name <> p.name  
WHERE  
    m.type IN ('table', 'view')  
AND  
    m.name NOT LIKE 'sqlite_%'  
ORDER BY  
    tableName,  
    columnName) WHERE columnType IN ('TEXT','CLOB');
```

leading to 53 potentially interesting and relevant columns. After manually inspecting those columns, the following few seemed relevant for NLP/ER Tasks for me


**Company Table**:
```sql
SELECT _registerNummerSuffix
	    ,company_number
		,current_status
		,federal_state
		,former_registrar
		,jurisdiction_code
		,name
		,native_company_number
		,register_art
		,register_flag_
		,register_flag_Note:
		,register_flag_Status information
		,register_nummer
		,registered_address
		,registered_office
		,registrar
		retrieved_at
FROM company;
```

Out of which the following are relevant for NLP/ER Tasks: 
- Name

**Officer Table**
```sql
SELECT city
		,company_id
		,dismissed
		,end_date
		,firstname
		,flag
		,lastname
		,maidenname
		,name
		,position
		,reference_no
		,start_date
		,title
		type
FROM officer; 
```

Out of which the following are relevant for NLP/ER Tasks: 
- flag


**Registrations Table**
```sql
SELECT  alternate_company_number
		,alternate_entity_type
		,alternate_jurisdiction_code
		,company_id
		,confidence
		,data_type
		,previous_company_number
		,previous_entity_type
		,previous_jurisdiction_code
		,previous_registration_end_date
		,publication_date
		,retrieved_at
		,sample_date
		,source_url
		,start_date
		,start_date_type
		,subsequent_company_number
		,subsequent_entity_type
		,subsequent_jurisdiction_code
		,subsequent_registration_start_date
FROM registrations;

```

Out of which the non seem relevant for NLP/ER Tasks.



#### Summary: 
This leads two potentially interesting columns: 
- `company.name` that contains the full company name
- `officer.flag` that contains controlling rules of individuals.


## Company.name
After consideration, following information might be relevant to extract: 

###### Company Type and Status
Identify the type of company based on suffixes like "GmbH," "e.K.," or "Union," which indicate the legal structure (e.g., GmbH for a limited liability company in Germany)

###### Geographical Information
Extract potential geographical indicators from the company name, such as "Algeria" in "Shell Algeria Zerafa GmbH," which might suggest a regional focus or origin.

###### Industry or Sector
Analyze keywords within the names that might indicate the industry, such as "Reederei" (shipping) or "Entertainment."

###### Branding or Product Focus
Identify specific branding elements or product focus from names like "Lime Juice Entertainment," which could hint at the company's market segment.

###### Owner or Founder Names
Extract personal names if present, such as "Markus Blum" in "Markus Blum Montagearbeiten e.K.," which might indicate the founder or owner.



## Entity Recognition: 
ER has been tested/performed on the two columns mentioned above. 
More can be found in the `playground_ER-NLP.ipynb` notebook.

