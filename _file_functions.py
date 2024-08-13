import os
import datetime

def get_file_age_in_minutes(filename, data_path = 'stock_data'):
    filename_with_extension = filename + '.json'
    directory = os.path.join(os.path.dirname(__file__), data_path)
    file_path = os.path.join(directory, filename_with_extension)
    if not os.path.exists(file_path):
        return 9999999999

    file_mod_time = os.path.getmtime(file_path)
    file_mod_datetime = datetime.datetime.fromtimestamp(file_mod_time)
    current_datetime = datetime.datetime.now()
    age_timedelta = current_datetime - file_mod_datetime
    age_in_minutes = age_timedelta.total_seconds() / 60

    return age_in_minutes