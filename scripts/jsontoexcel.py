import pandas as pd
import json
import os
import openpyxl
import numpy as np


class jsonToExcel:
    def __init__(self):
        self.associate_count = 30 #Change number here if there is a larger batch, or smaller if you want a cleaner excel sheet to match associate count

    def main(self):
        try:
            json_data = self.retrieveQuizDataAndNames()
        except:
            print("\nYou must have at least the exported quiz results in the input folder, batch report is optional.")
            return
        parsed_json_data = self.parseJsonData(json_data)
        self.exportToExcel(parsed_json_data)

        print("\nSuccess! Check the output folder for the Excel file.")


    def retrieveQuizDataAndNames(self):
        """Retrieves exported quiz data from the inputs folder, as well as the corresponding batch report to match
        associate ids with names.

        output: 
            jason_data_dict: [dict]
        """
        json_input_path = os.path.join(os.getcwd(), "input")
        json_files = [ x for x in os.listdir(json_input_path) if x.endswith("json")] #Checking for every json file inside the inputs folder

        json_data = list()
        for json_file in json_files:
            json_file_path = os.path.join(json_input_path, json_file)
            with open (json_file_path, "r") as f:
                json_data.append(json.load(f))

        json_data_dict = self.identifyJsonFile(json_data) #Changing the data from list to dict format alongside identifying which one is the quiz results, and the batch report

        return json_data_dict

    def identifyJsonFile(self, json_data):
        """Identifies the two given json files to see which one is the quiz results, and which is the batch report.

        inputs:
            json_data: [list: string]

        output: 
            json_data_dict: [dict]
        """
        json_data_dict = {}

        if(len(json_data)) > 1: #Checking if we have both the batch report and quiz results, or just the quiz results
            try: #Seeing if the salesforce batch id exists in the json file, if so, we know its the batch report
                sf_id = json_data[0]["batchSfId"] #Exception thrown here if files are in the correct order
                json_data_dict["quizResults"] = json_data[1] #Switching the order of the json files to be aligned for future use (0 is batch report, 1 is quiz results)
                json_data_dict["batchReport"] = json_data[0]

            except: #We know that the first json file in the list is not the batch report (they are in the correct order, with quiz results being first in the list, so we do nothing)
                pass

        else: #We only have the quiz results
            json_data_dict["quizResults"] = json_data[0]
            json_data_dict["batchReport"] = False

        return json_data_dict

    def exportToExcel(self, json_data_df):
        """Transforms the fully formatted DataFrame into a readable format for Excel.

        inputs:
            json_data_df: [Pandas DataFrame]

        output: 
            .xlsx file
        """
        df = json_data_df.to_excel("output/quizResults.xlsx")

    def matchAssociateIDtoName(self, raw_json_batch_report, associate_ids, associate_ids_set):
        """Matches the inputted associate salesforce ids to their name from the batch report.

        inputs:
            raw_json_batch_report: [JSON]
            associate_ids: [array: str]
            associate_ids_set: [set: str]

        output:
            associate_names: [array: str]
        """
        associate_names = [''] * (len(associate_ids)-1) #Empty array of strings to match indexes to associate id
        not_found = len(associate_ids) - 1

        while (not_found > 1): #We iterate through the JSON data from the batch report until we match all the ids to their names
            quizzes = raw_json_batch_report["quizzes"]
            for i in range(len(quizzes)):
                grades = quizzes[i]["grades"]
                for j in range(len(grades)):
                    assoc_sf_id = grades[j]["traineeSfId"]
                    if (assoc_sf_id not in associate_ids_set): #If we already have the salesforce id
                        associate_names[associate_ids.index(assoc_sf_id)] = f'{grades[j]["traineeFirstName"]} {grades[j]["traineeLastName"]}' #Checks for the index and adds it to the corresponding index in the names array
                        not_found -= 1 #Decrease until we hit 0

        associate_names = list(filter(len, associate_names)) #Removes all the elements in the array with an empty string

        return associate_names

    def parseJsonData(self, json_data):
        """Parses the raw json file into a formatted version for excel.

        inputs:
            json_data: [JSON]

        output: 
            df: [Pandas DataFrame]
        """
        raw_json_quiz = json_data["quizResults"]["quizzes"]
        raw_json_batch_report = json_data["batchReport"]
        associates = ['']*self.associate_count #Preset with empty strings
        assoc_ind = 0
        trainee_ids = set()
        quizzes = dict() #Both the quiz name, and a list of grades
        pandas_column_names = ['']*(self.associate_count-1) #Preset with empty strings
        pan_col_ind = 0
        pandas_row_values = list()
        for i in range(len(raw_json_quiz)): #Iterate over all the quizzes
            quiz_scores = np.zeros(self.associate_count)
            quizTitle = raw_json_quiz[i]["title"] + f' ({raw_json_quiz[i]["category"]})'
            pandas_column_names[pan_col_ind] = quizTitle #Replaces empty string to a list of all the quiz names and categories associated with it
            pan_col_ind += 1
            for j in range(len(raw_json_quiz[i]['grades'])): #Iterate over each associate id/grade for each quiz
                associate = raw_json_quiz[i]['grades'][j]
                if (associate["traineeId"] not in trainee_ids): #If we haven't already found this associate before, add the associate name to the associates list
                    associates[assoc_ind] = (associate["trainee"]) #Replacing an empty string with the associate name
                    assoc_ind+=1
                trainee_ids.add(associate["traineeId"])
                quiz_scores[associates.index(associate["trainee"])] = float((associate["grade"])) #Insert the grade in the correct row matched to the associate index

            quizzes[quizTitle] = quiz_scores #Adds the associated quiz scores alongside the quiz name
            pandas_row_values.append(quiz_scores.tolist())

        df = self.quizScoresToDataFrame(pandas_column_names, pandas_row_values, associates, raw_json_batch_report, trainee_ids)        

        return df

    def quizScoresToDataFrame(self, column_names, row_values, associate_ids, raw_json_batch_report, trainee_ids):
        """Translates the associate information alongside their quiz scores to a Pandas DataFrame.

        inputs:
            column_names: [list: str]
            row_values: [list: str]
            associate_ids: [array: str]
            raw_json_batch_report: [JSON]
            trainee_ids: [set: str]

        output:
            df: [Pandas DataFrame]
        """
        try: #Checking if we have the batch report file, if so we create the names column with the associates names
            associate_names = self.matchAssociateIDtoName(raw_json_batch_report, associate_ids, trainee_ids) #Returns a list of names associated with each associate ID
            column_names.insert(0,"Name") #Prepends Name column for pd df
            row_values.insert(0, associate_names)
        except: #If we don't have the batch report, we supply the IDs of the associates instead of the names
            column_names.insert(0,"ID") #Prepends ID column for pd df
            row_values.insert(0, associate_ids)

        df = pd.DataFrame(row_values, columns=column_names, dtype=object) #Creating the Data Frame
        df = df.T #Transposes the Data Frame 90 degrees CCW
        column_names = list(filter(len, column_names)) #Removes all the elements in the array with an empty string
        df.columns=column_names #Renames the columns after rotation
        df.index = np.arange(0, self.associate_count, 1) #Renames the indexes after rotation

        return df      

        
    