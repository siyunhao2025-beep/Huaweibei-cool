Option Explicit

' Re-paginate a DOCX in Microsoft Word and export PDF.
' Usage: cscript //nologo render_word.vbs input.docx output.pdf headings.json
' The source is opened read-only; no document is saved or modified.

Const wdExportFormatPDF = 17
Const wdStatisticPages = 2
Const wdActiveEndPageNumber = 3
Const wdDoNotSaveChanges = 0
Const wdExportOptimizeForPrint = 0
Const wdExportAllDocument = 0
Const wdExportDocumentContent = 0
Const wdExportCreateNoBookmarks = 0

Dim fso, args, inputPath, outputPath, jsonPath
Set fso = CreateObject("Scripting.FileSystemObject")
Set args = WScript.Arguments
If args.Count < 2 Then
  WScript.Echo "Usage: cscript //nologo render_word.vbs input.docx output.pdf [headings.json]"
  WScript.Quit 2
End If
inputPath = fso.GetAbsolutePathName(args(0))
outputPath = fso.GetAbsolutePathName(args(1))
If args.Count >= 3 Then
  jsonPath = fso.GetAbsolutePathName(args(2))
Else
  jsonPath = outputPath & ".headings.json"
End If
If Not fso.FileExists(inputPath) Then
  WScript.Echo "Input file does not exist: " & inputPath
  WScript.Quit 2
End If
If LCase(inputPath) = LCase(outputPath) Then
  WScript.Echo "Input and output must be different files"
  WScript.Quit 2
End If

Dim word, doc, pages, headingJson, headingCount, p, text, level, page
On Error Resume Next
Set word = CreateObject("Word.Application")
If Err.Number <> 0 Then
  WScript.Echo "Unable to start Microsoft Word: " & Err.Description
  WScript.Quit 3
End If
Err.Clear
word.Visible = False
word.DisplayAlerts = 0
Set doc = word.Documents.Open(inputPath, False, True, False)
If Err.Number <> 0 Then
  WScript.Echo "Unable to open DOCX: " & Err.Description
  word.Quit
  WScript.Quit 3
End If
Err.Clear
On Error GoTo 0

doc.Repaginate
pages = doc.ComputeStatistics(wdStatisticPages)
headingCount = 0
headingJson = ""

For Each p In doc.Paragraphs
  text = Trim(Replace(Replace(p.Range.Text, Chr(13), ""), Chr(7), ""))
  If Len(text) > 0 Then
    level = HeadingLevel(p.Style)
    If level > 0 Then
      page = p.Range.Information(wdActiveEndPageNumber)
      headingCount = headingCount + 1
      If headingCount > 1 Then headingJson = headingJson & ","
      headingJson = headingJson & "{""text"":""" & JsonEscape(text) & """,""level"":" & CStr(level) & ",""physical_page"":" & CStr(page) & "}"
    End If
  End If
Next

Dim json
json = "{""physical_pages"":" & CStr(pages) & ",""printed_page_offset"":0,""headings"": [" & headingJson & "]}"
WriteUtf8 jsonPath, json

On Error Resume Next
doc.ExportAsFixedFormat outputPath, wdExportFormatPDF, False, wdExportOptimizeForPrint, wdExportAllDocument, 0, 0, wdExportDocumentContent, wdExportCreateNoBookmarks, False, False, False
If Err.Number <> 0 Then
  WScript.Echo "PDF export failed: " & Err.Description
  doc.Close wdDoNotSaveChanges
  word.Quit
  WScript.Quit 4
End If
doc.Close wdDoNotSaveChanges
word.Quit
On Error GoTo 0
WScript.Echo "Pages=" & pages
WScript.Echo "PDF=" & outputPath
WScript.Echo "Headings=" & jsonPath
WScript.Quit 0

Function HeadingLevel(styleValue)
  Dim s
  s = LCase(CStr(styleValue))
  If InStr(s, "heading 1") > 0 Or InStr(s, "heading1") > 0 Or InStr(s, "huawei heading 1") > 0 Then
    HeadingLevel = 1
  ElseIf InStr(s, "heading 2") > 0 Or InStr(s, "heading2") > 0 Or InStr(s, "huawei heading 2") > 0 Then
    HeadingLevel = 2
  ElseIf InStr(s, "heading 3") > 0 Or InStr(s, "heading3") > 0 Or InStr(s, "huawei heading 3") > 0 Then
    HeadingLevel = 3
  Else
    HeadingLevel = 0
  End If
End Function

Function JsonEscape(value)
  Dim s
  s = CStr(value)
  s = Replace(s, "\", "\\")
  s = Replace(s, Chr(34), "\" & Chr(34))
  s = Replace(s, vbCr, "\r")
  s = Replace(s, vbLf, "\n")
  JsonEscape = s
End Function

Sub WriteUtf8(path, content)
  Dim stream
  Set stream = CreateObject("ADODB.Stream")
  stream.Type = 2
  stream.Charset = "utf-8"
  stream.Open
  stream.WriteText content
  stream.SaveToFile path, 2
  stream.Close
End Sub
