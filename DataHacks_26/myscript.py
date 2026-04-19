
#Cell 1


# import os

# # Notice the 'r' before the quote!
# path = "C:/Users/andre/OneDrive/Documents/SD Fish - Data"

# # Change the "Office" to that folder
# os.chdir(path)

# print("I am now standing in:", os.path.dirname(path))





#Cell 2

# import pandas as pd
# import marimo as mo






#Cell 3


# # Load your two species files
# # (Check that these filenames match exactly what you saved on your computer)
# df_garibaldi = pd.read_csv('garibaldi_clean.csv.csv')
# df_shark = pd.read_csv('leopard_shark_clean.csv.csv')

# # Add the 'presence' label and species name
# df_garibaldi['species'] = 'Garibaldi'
# df_garibaldi['presence'] = 1

# df_shark['species'] = 'Leopard Shark'
# df_shark['presence'] = 1

# # Combine them into one master list
# df_master = pd.concat([df_garibaldi, df_shark])

# # Round the coordinates so they match the Argo 'Grid' later
# df_master['lat_round'] = df_master['latitude'].round(1)
# df_master['lon_round'] = df_master['longitude'].round(1)

# # This line lets you see the first 5 rows in Marimo to make sure it worked
# df_master.head()