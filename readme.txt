# File Pre Processing Automation before DX Process
Problem Statement
As discussed, the following steps need to be taken for each software provider:

Rockend & Property IQ:
State Column: Validate entries against the correct state/territory formats (NSW, VIC, QLD, SA, WA, ACT, TAS, NT). Change to the correct format or delete if unclear.
Postcode Column: Ensure all entries are exactly 4 digits long. Anything shorter, longer, or containing letters will be deleted.
Maxsoft:
State/Postcode Column: Similar validation as for Rockend or Property IQ, although issues are less common for Maxsoft clients.
Phone/Mobile/Fax Columns: Check for entries longer than 15 characters and ensure they contain only alphanumeric characters. Any invalid entries will be deleted.
Email Column: Ensure emails do not exceed 130 characters. Only the first valid email will be retained if multiple emails are present. Invalid or excessively long emails will be deleted. This is crucial because the clients’ systems may crash if they attempt to import files containing these problematic entries.
Stratasphere:
No processing needed, as this software provider typically has no incorrect data and can be uploaded directly to the Engine.
How We Are Solving It
To address the above issues, we have implemented the following processing logic in our application:

General Handling:

For both Rockend and Property IQ:
State Column: Validate against a predefined list of acceptable state codes. If invalid, set the state entry to blank.
Postcode Column (PCode): Ensure all entries are exactly 4 digits long. If not, set the field to blank.
Maxsoft Specific Handling:

Similar checks for the State and Postcode columns, though issues are less common.
Phone/Mobile/Fax Columns: Check for a maximum length of 15 characters and ensure only alphanumeric characters are present. If invalid, set the field to blank.
Email Column: Ensure it does not exceed 130 characters, and retain only the first valid email. If invalid, set the field to blank.
This structured approach ensures that we maintain data integrity and prevent issues during the import process for all software providers.