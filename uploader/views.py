import pandas as pd
import matplotlib.pyplot as plt
# import urllib, base64
from io import BytesIO
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import UploadFileForm
# from .models import ProcessedData
import io
import re
from django.conf import settings
import os
import warnings
warnings.filterwarnings('ignore')

global_result_df1 = None
global_result_df2 = None
merged_df = None

def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file1 = request.FILES.get('file1')
            file2 = request.FILES.get('file2')
            if file1 and file2:
                handle_uploaded_file(file1, file2)
                return redirect('upload_success')
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})


def handle_uploaded_file(f1,f2):
    global merged_df
    file_data1 = BytesIO(f1.read())
    process_file1(file_data1)
    file_data2 = BytesIO(f2.read())
    process_file2(file_data2)
    merged_df = pd.concat([global_result_df1, global_result_df2], axis=0)


def process_file1(uploaded_file):
    global global_result_df1  # Declare global to modify the global variable
    import os
    # extracting date information
    # read excel 1st row
    sample = pd.read_excel(uploaded_file, nrows=1)
    first_row = sample.iloc[0]
    text = first_row.values[0]

    # applying regular expression to find out date ---> month and year information
    pattern = r'\b[A-Za-z]+\s\d{4}\b'
    match = re.search(pattern, text)
    year_info = match.group()
    month = year_info.split(" ")[0][:3]
    year = year_info.split(" ")[-1]

    # reading input file ### segment section
    ip_1_seg_df = pd.read_excel(uploaded_file, sheet_name='Segmentwise Report', header=1)
    ip_1_seg_df = ip_1_seg_df.rename(columns={'Unnamed: 0': 'General Insurers'})
    ip_1_seg_df = ip_1_seg_df.iloc[1:, :-5]

    # reading input file ### health section
    ip_1_health_df = pd.read_excel(uploaded_file, sheet_name='Health Portfolio', header=2)
    ip_1_health_df = ip_1_health_df.rename(columns={'Unnamed: 0': 'General Insurers'})
    ip_1_health_df = ip_1_health_df.iloc[1:, :-4]

    # reading input file ### Miscellaneous portfolio
    ip_1_msc_df = pd.read_excel(uploaded_file, sheet_name='Miscellaneous portfolio', header=1)
    ip_1_msc_df = ip_1_msc_df.rename(columns={'Unnamed: 0': 'General Insurers'})
    ip_1_msc_df = ip_1_msc_df.iloc[1:, :-4]

    # reading master excel file for mapping
    master_name_df = pd.read_excel(settings.MASTER_FILE_PATH, sheet_name='name')
    master_category_df = pd.read_excel(settings.MASTER_FILE_PATH, sheet_name='category')
    master_lob_df = pd.read_excel(settings.MASTER_FILE_PATH, sheet_name='lob', header=None)

    # extracting info from master for mapping purpose
    ref_columns_list = list(pd.Series(master_lob_df[0].values).str.strip())  # product names
    ref_columns_list.insert(0, 'General Insurers')

    ogname_to_clubname_dict = dict(
        zip(master_name_df.insurer, master_name_df.clubbed_name))  # original name to clubbed name

    clubname_to_category_dict = dict(
        zip(master_category_df.clubbed_name, master_category_df.category))  # clubbed name to category

    # further cleaning of input file
    # only keeping General Insurers, removing element like previous, other info. applied in all sheets
    ip_1_seg_df = ip_1_seg_df[ip_1_seg_df['General Insurers'].isin(list(ogname_to_clubname_dict.keys()))]
    ip_1_health_df = ip_1_health_df[ip_1_health_df['General Insurers'].isin(list(ogname_to_clubname_dict.keys()))]
    ip_1_msc_df = ip_1_msc_df[ip_1_msc_df['General Insurers'].isin(list(ogname_to_clubname_dict.keys()))]

    # merging dataframes
    df = pd.merge(left=ip_1_seg_df, right=ip_1_health_df, how='left', on="General Insurers")
    df = pd.merge(left=df, right=ip_1_msc_df, how='left', on="General Insurers")

    # imputing 0 for null value
    df.fillna(0, inplace=True)

    # cleaning df columns
    df.columns = df.columns.str.replace('  ', ' ').str.strip()

    # new df --- only with required columns
    new_df = df[ref_columns_list]

    # cleaning new_df
    new_df['General Insurers'] = new_df['General Insurers'].str.strip()

    # pandas melting for analysis purpose
    result = pd.melt(new_df, id_vars=['General Insurers'],
                     value_vars=[col for col in new_df.columns if col != 'General Insurers'], ignore_index=True)
    result.sort_values('General Insurers', inplace=True)

    # adding additional information
    result['clubbed_name'] = result['General Insurers'].map(ogname_to_clubname_dict)
    result['category'] = result['clubbed_name'].map(clubname_to_category_dict)
    result['Year'] = year
    result["Month"] = month

    # refining result
    result.drop(['General Insurers'], inplace=True, axis=1)
    result = result.rename(columns={'variable': 'Product'})
    result = result.loc[:, ['Year', 'Month', 'category', 'clubbed_name', 'Product', 'value']]
    result.reset_index(inplace=True, drop=True)

    # Generate the output CSV name using the original file name (if available)
    original_file_name = uploaded_file.name if hasattr(uploaded_file, 'name') else 'output'
    output_csv_name = os.path.splitext(original_file_name)[0] + "_output.csv"

    result.to_csv(output_csv_name, index=False)

    global_result_df1 = result
    return result


def process_file2(uploaded_file):
    global global_result_df2  # Declare global to modify the global variable
    import os
    # extracting date information
    # read excel 1st row
    sample = pd.read_excel(uploaded_file, nrows=1)
    first_row = sample.iloc[0]
    text = first_row.values[0]

    # applying regular expression to find out date ---> month and year information
    pattern = r'\b[A-Za-z]+\s\d{4}\b'
    match = re.search(pattern, text)
    year_info = match.group()
    month = year_info.split(" ")[0][:3]
    year = year_info.split(" ")[-1]

    # reading input file ### segment section
    ip_1_seg_df = pd.read_excel(uploaded_file, sheet_name='Segmentwise Report', header=1)
    ip_1_seg_df = ip_1_seg_df.rename(columns={'Unnamed: 0': 'General Insurers'})
    ip_1_seg_df = ip_1_seg_df.iloc[1:, :-5]

    # reading input file ### health section
    ip_1_health_df = pd.read_excel(uploaded_file, sheet_name='Health Portfolio', header=2)
    ip_1_health_df = ip_1_health_df.rename(columns={'Unnamed: 0': 'General Insurers'})
    ip_1_health_df = ip_1_health_df.iloc[1:, :-4]

    # reading input file ### Miscellaneous portfolio
    ip_1_msc_df = pd.read_excel(uploaded_file, sheet_name='Miscellaneous portfolio', header=1)
    ip_1_msc_df = ip_1_msc_df.rename(columns={'Unnamed: 0': 'General Insurers'})
    ip_1_msc_df = ip_1_msc_df.iloc[1:, :-4]

    # reading master excel file for mapping
    master_name_df = pd.read_excel(settings.MASTER_FILE_PATH, sheet_name='name')
    master_category_df = pd.read_excel(settings.MASTER_FILE_PATH, sheet_name='category')
    master_lob_df = pd.read_excel(settings.MASTER_FILE_PATH, sheet_name='lob', header=None)

    # extracting info from master for mapping purpose
    ref_columns_list = list(pd.Series(master_lob_df[0].values).str.strip())  # product names
    ref_columns_list.insert(0, 'General Insurers')

    ogname_to_clubname_dict = dict(
        zip(master_name_df.insurer, master_name_df.clubbed_name))  # original name to clubbed name

    clubname_to_category_dict = dict(
        zip(master_category_df.clubbed_name, master_category_df.category))  # clubbed name to category

    # further cleaning of input file
    # only keeping General Insurers, removing element like previous, other info. applied in all sheets
    ip_1_seg_df = ip_1_seg_df[ip_1_seg_df['General Insurers'].isin(list(ogname_to_clubname_dict.keys()))]
    ip_1_health_df = ip_1_health_df[ip_1_health_df['General Insurers'].isin(list(ogname_to_clubname_dict.keys()))]
    ip_1_msc_df = ip_1_msc_df[ip_1_msc_df['General Insurers'].isin(list(ogname_to_clubname_dict.keys()))]

    # merging dataframes
    df = pd.merge(left=ip_1_seg_df, right=ip_1_health_df, how='left', on="General Insurers")
    df = pd.merge(left=df, right=ip_1_msc_df, how='left', on="General Insurers")

    # imputing 0 for null value
    df.fillna(0, inplace=True)

    # cleaning df columns
    df.columns = df.columns.str.replace('  ', ' ').str.strip()

    # new df --- only with required columns
    new_df = df[ref_columns_list]

    # cleaning new_df
    new_df['General Insurers'] = new_df['General Insurers'].str.strip()

    # pandas melting for analysis purpose
    result = pd.melt(new_df, id_vars=['General Insurers'],
                     value_vars=[col for col in new_df.columns if col != 'General Insurers'], ignore_index=True)
    result.sort_values('General Insurers', inplace=True)

    # adding additional information
    result['clubbed_name'] = result['General Insurers'].map(ogname_to_clubname_dict)
    result['category'] = result['clubbed_name'].map(clubname_to_category_dict)
    result['Year'] = year
    result["Month"] = month

    # refining result
    result.drop(['General Insurers'], inplace=True, axis=1)
    result = result.rename(columns={'variable': 'Product'})
    result = result.loc[:, ['Year', 'Month', 'category', 'clubbed_name', 'Product', 'value']]
    result.reset_index(inplace=True, drop=True)

    # Generate the output CSV name using the original file name (if available)
    original_file_name = uploaded_file.name if hasattr(uploaded_file, 'name') else 'output'
    output_csv_name = os.path.splitext(original_file_name)[0] + "_output.csv"

    result.to_csv(output_csv_name, index=False)

    global_result_df2 = result
    return result

def display_plot(request):
    global merged_df

    if merged_df is not None:
        # Create a bar plot
        plt.figure(figsize=(10, 6))
        plt.bar(merged_df['Product'], merged_df['value'], color='skyblue')
        plt.xlabel('Product')
        plt.ylabel('Value')
        plt.title('Product vs Value')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Save the plot to a file
        plot_path = settings.PLOT_FILE_PATH
        plt.savefig(plot_path)
        plt.close()

        # Display the saved plot
        with open(plot_path, 'rb') as plot_file:
            response = HttpResponse(plot_file.read(), content_type='image/png')
            response['Content-Disposition'] = 'inline; filename="plot.png"'
            return response

    else:
        return HttpResponse("No data available to plot.")


def download_output(request):
    global merged_df
    if merged_df is not None:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            merged_df.to_excel(writer, index=False)
        output.seek(0)
        # Set up the response to send the Excel file
        response = HttpResponse(output.read(),
                                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="FinalFile.xlsx"'
        return response
    else:
        return HttpResponse("No data available to download.")


def upload_success(request):
    return render(request, 'upload_success.html')
