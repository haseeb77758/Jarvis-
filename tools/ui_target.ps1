Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Jarvis CI Target'
$form.Width = 420
$form.Height = 270
$button = New-Object System.Windows.Forms.Button
$button.Text = 'Jarvis Test Button'
$button.Width = 200
$button.Top = 20
$button.Left = 20
$label = New-Object System.Windows.Forms.Label
$label.Text = 'Waiting for test'
$label.Width = 300
$label.Top = 80
$label.Left = 20
$button.Add_Click({ $label.Text = 'INVOKE PASSED' })
$inputBox = New-Object System.Windows.Forms.TextBox
$inputBox.AccessibleName = 'Jarvis test input'
$inputBox.Width = 300
$inputBox.Top = 120
$inputBox.Left = 20
$inputBox.Add_TextChanged({ if ($inputBox.Text -eq 'Hello Jarvis') { $label.Text = 'TYPE PASSED' } })
$form.Add_Shown({ $form.ActiveControl = $inputBox })
$form.Controls.Add($inputBox)
$form.Controls.Add($button)
$form.Controls.Add($label)
[System.Windows.Forms.Application]::Run($form)
