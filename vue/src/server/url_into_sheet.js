const { google } = require("googleapis");
const path = require('path');

const currentDirrectory = `${path.dirname(require.main.filename)}`

const auth = new google.auth.GoogleAuth({
  keyFile: `${currentDirrectory}/../../../secrets/googlekey.json`,
  scopes: [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
  ],
});
const sheets = google.sheets({version: "v4", auth});

async function createSheetWithTitle(spreadsheetId, title) {
  const resource = {
    requests: [
      {
        addSheet: {
          properties: {
            title: title
          }
        }
      }
    ]
  };
  const response = await sheets.spreadsheets.batchUpdate({
    spreadsheetId,
    resource,
  });
  console.log(response.data);
  sheets.spreadsheets.get()
  return response.data
}

async function deleteSheet(spreadsheetId, sheetId) {
  const resource = {
    requests: [
      {
        deleteSheet: {
          sheetId,
        },
      },
    ],
  };
  const response = await sheets.spreadsheets.batchUpdate({
    spreadsheetId,
    resource,
  });
  console.log(response.data);
}


async function createSheetIfNotExists(spreadsheetId, title) {
  const spreadsheet = await sheets.spreadsheets.get({spreadsheetId: spreadsheetId});
  var sheet = spreadsheet.data.sheets.find(s => s.properties.title === title);
  if (sheet !== undefined) {
    return sheet
  }
  return createSheetWithTitle(spreadsheetId, title)
}

async function updateCells(spreadsheetId, range, values) {
  const resource = {
    values,
  };
  try {
    const response = await sheets.spreadsheets.values.update({
      spreadsheetId,
      range,
      valueInputOption: 'USER_ENTERED',
      resource,
    });
    console.log(response.data);
  } catch (err) {
    console.error(err);
  }
}

async function updateNamedSheet(spreadsheetId, sheetName, url, time) {
  const range = `${sheetName}!A1:B2`;
  const values = [
    ['IP', url],
    ['last update', time],
  ];
  await updateCells(spreadsheetId, range, values)
}

async function findRangeByValue(spreadsheetId, sheetName, value) {
  const range = `${sheetName}!A1:C`;
  const response = await sheets.spreadsheets.values.get({
    spreadsheetId,
    range,
  });
  const rows = response.data.values;
  var targetRow = response.data.values ? response.data.values.length + 1 : 1;
  for (let i = 0; i < rows.length; i++) {
    if (rows[i].indexOf(value) !== -1) {
      targetRow = i + 1;
      break;
    }
  }
  return `${sheetName}!A${targetRow}:C${targetRow}`;
}

async function updateMainSheet(spreadsheetId, sheetName, url, time) {
  const range = await findRangeByValue(spreadsheetId, 'main', sheetName);
  const values = [
    [sheetName, time, url],
  ];
  await updateCells(spreadsheetId, range, values)
}

async function saveUrlToSpreadsheet(spreadsheetId, sheetName, url) {
  const time = new Date().toString();
  await createSheetIfNotExists(spreadsheetId, sheetName);
  await updateNamedSheet(spreadsheetId, sheetName, url, time)
  await updateMainSheet(spreadsheetId, sheetName, url, time)
}

module.exports = {
  writeUrlToGoogleSheet: saveUrlToSpreadsheet
};
