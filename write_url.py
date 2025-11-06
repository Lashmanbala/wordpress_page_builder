
def write_url_to_sheet(sheet_service, spreadsheetId, sheet_name, column, page_url, city_name, cities, logger):
    """Writes the generated WordPress page URL back to the specified Google Sheet."""

    try:
        if not all([sheet_service, spreadsheetId, sheet_name, column, page_url, city_name, cities]):
            logger.error("❌ Missing one or more required parameters in write_url_to_sheet()")
            return False
            
        row_index = None

        for i, row in enumerate(cities, start=2): # 1st row is title so, starting from 2nd row
            if row.strip() == city_name:
                row_index = i
                break

        if row_index:
            # Update column B in the correct row
            sheet_service.spreadsheets().values().update(
                spreadsheetId=spreadsheetId,
                range=f"{sheet_name}!{column}{row_index}",
                valueInputOption="RAW",
                body={"values": [[page_url]]}
            ).execute()
            logger.info(f"✅ Link updated in the sheet successfully in {sheet_name}!{column}{row_index}") 
            return True
        else:
            logger.info(f"⚠️ City '{city_name}' not found in sheet!")               
            return False      

    except Exception as e:
        logger.error(f"❌ Error while writing URL for '{city_name}': {e}")
        return False
'''
# def write_url_to_sheet1(sheet_service, spreadsheetId, sheet_name, column, page_url, city_name, cities, logger):

#     row_index = None

#     for i, row in enumerate(cities, start=2): # 1st row is title so, starting from 2nd row
#         if row == city_name:
#             row_index = i
#             break

#     if row_index:
#         # Update column B in the correct row
#         sheet_service.spreadsheets().values().update(
#             spreadsheetId=spreadsheetId,
#             range=f"{sheet_name}!{column}{row_index}",
#             valueInputOption="RAW",
#             body={"values": [[page_url]]}
#         ).execute()
#         logger.info(f"✅ Link updated in the sheet successfully!") 
#     else:
#         logger.info(f"⚠️ City '{city_name}' not found in sheet!")               


# def write_url_to_sheet2(sheet_service, spreadsheetId, sheet_name, column, page_url, city_name, cities, logger):

#     row_index = None

#     for i, row in enumerate(cities, start=2): # 1st row is title so, starting from 2nd row
#         if row == city_name:
#             row_index = i
#             break

#     if row_index:
#         # Update column B in the correct row
#         sheet_service.spreadsheets().values().update(
#             spreadsheetId=spreadsheetId,
#             range=f"{sheet_name}!{column}{row_index}",
#             valueInputOption="RAW",
#             body={"values": [[page_url]]}
#         ).execute()
#         logger.info(f"✅ Link updated in the sheet successfully!") 
#     else:                                                  
#         logger.info(f"⚠️ City '{city_name}' not found in sheet!")                                               
'''