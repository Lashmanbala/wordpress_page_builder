def write_url_to_sheet(sheet_service, spreadsheetId, sheet_name, page_url, city_name, cities):

    row_index = None

    for i, row in enumerate(cities, start=2): # 1st row is title so, starting from 2nd row
        if row and row[0] == city_name:
            row_index = i
            break

    if row_index:
        # Update column B in the correct row
        sheet_service.spreadsheets().values().update(
            spreadsheetId=spreadsheetId,
            range=f"{sheet_name}!B{row_index}",
            valueInputOption="RAW",
            body={"values": [[page_url]]}
        ).execute()
        return f"✅ Link updated in the sheet successfully!"
    else:
        return f"⚠️ City '{city_name}' not found in sheet!"                                                     