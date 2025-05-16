import requests
import xml.etree.ElementTree as ET
import pandas as pd

# URL for Tally's HTTP server
TALLY_URL = "http://localhost:9000"

# XML request to fetch all Ledgers
xml_request = """
<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Export Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Ledgers</REPORTNAME>
                <STATICVARIABLES>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>
"""

# Send request to Tally
response = requests.post(TALLY_URL, data=xml_request)

# Parse XML response
root = ET.fromstring(response.text)

# Extract Ledger Names
ledgers = []
for ledger in root.findall(".//LEDGER"):
    name = ledger.find("NAME").text if ledger.find("NAME") is not None else ""
    parent = ledger.find("PARENT").text if ledger.find("PARENT") is not None else ""
    opening_balance = ledger.find("OPENINGBALANCE").text if ledger.find("OPENINGBALANCE") is not None else ""
    ledgers.append({
        "Name": name,
        "Parent Group": parent,
        "Opening Balance": opening_balance
    })

# Convert to DataFrame
df = pd.DataFrame(ledgers)

# Save to Excel and CSV
df.to_excel("Tally_Ledgers.xlsx", index=False)

print("Export completed: Tally_Ledgers.xlsx")
