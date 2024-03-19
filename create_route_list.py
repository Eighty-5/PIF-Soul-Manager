import csv

with open('routes.csv', newline='') as csvfile, open('myproject/blueprints/main/templates/route_list.html', 'w') as htmlfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        htmlfile.write(f'<option value="{row['id']}">{row['route']}</option>\n')
