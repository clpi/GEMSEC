# -*- coding: utf-8 -*-
"""
Created on Tue Mar 19 10:49:52 2019

@author: Chris

This class is a highly-efficient calculator of Total Similarity Scores for a
specified list of peptides as compared to known strong binding peptides.
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.linear_model import ElasticNet
from sklearn.model_selection import GridSearchCV

class AlignmentCalculator(object):
    
    #   Peptide and binder sequence length must be the same
    #   Format of peptides and binders csv:
    #   0  1  2  3  4  5  6  7  8  ...  n
    #   A  I  I  D  Y  I  A  Y  M  ...  S
    #   A  I  Y  D  T  M  Q  Y  V  ...  G
    
    # TODO: Allow for non-separated peptide strings to be stored to prevent
    # downtime of storing peptides and binders into single strings

    def __init__(self, p_path = None, b_path = None, TSS_path = None):
        self.AA = list("ACDEFGHIKLMNPQRSTVWY")
        self.cluster_keys = list("abcehipr")
        self.matrices = dict.fromkeys(self.cluster_keys)
        for key in self.cluster_keys:
            self.matrices[key] = pd.read_csv("./improved/cluster_" + key + ".csv", index_col = 0)
        if TSS_path is not None: 
            self.import_TSS(TSS_path)
            self.total_scores = self.__create_dict()
        self.__store_values(p_path, b_path)

    def __store_values(self, p_path, b_path):
        if p_path is not None:
            self.p = pd.read_csv(p_path)  
            if "Unnamed: 0" in list(self.p.columns):
                self.p = self.p.set_index("Unnamed: 0")
            self.length = len(list(self.p.columns))
            print("storing peptides...")
            self.peptides = [''.join(list(self.p.iloc[m, :])) for m in range(len(list(self.p.index)))]
        if b_path is not None:
            self.b = pd.read_csv(b_path)
            if "Unnamed: 0" in list(self.b.columns):
                self.b = self.b.set_index("Unnamed: 0")
            self.length = len(list(self.b.columns))
            print("storing binders...")
            self.binders = [''.join(list(self.b.iloc[n, :])) for n in range(len(list(self.b.index)))]
            
    def __create_dict(self):
        print("matrix dict setup...")
        dist = dict.fromkeys(self.cluster_keys)
        for key in dist:
            dist[key] = dict.fromkeys(self.AA)
            for aa in dist[key]:
                dist[key][aa] = dict.fromkeys(self.AA)
                for aa2 in dist[key][aa]:
                    dist[key][aa][aa2] = self.matrices[key].loc[aa, aa2]
        print("Total differences setting up...")
        total_scores = dict.fromkeys(self.cluster_keys)
        for key in self.cluster_keys:
            total_scores[key] = dict.fromkeys(self.AA)
            for aa in total_scores[key]:
                total_scores[key][aa] = dict.fromkeys(range(self.length))
                for l in range(self.length):
                    total_score = 0   
                    for n in range(len(self.binders)):
                         total_score += dist[key][aa][self.binders[n][l]]
                    total_scores[key][aa][l] = total_score
        return total_scores
                
    
    def set_peptides(self, p_path):
        self.__store_values(p_path, None)
    
    def set_binders(self, b_path):
        self.__store_values(None, b_path)
    
    #   Format of TSS.csv file must be:
    #              a    b    c    ...  r   
    #   AIIDYIAYM  574  641  662  ...  599
    #   AIYDTMQYV  612  690  742  ...  640
    #   ALATFTVNI  719  782  829  ...  744  
    
    def import_TSS(self, TSS_path):
        self.tss_df = pd.read_csv(TSS_path)
        self.tss_df.set_index('Unnamed: 0', inplace = True)
        self.peptides = list(self.tss_df.index)
        self.length = len(self.peptides[0])
        
    def calculate_TSS(self, use_counts = False):
        if self.p is None or self.b is None:
            raise Exception("List of peptides or binders not set")
        if len(list(self.p.columns)) != len(list(self.b.columns)):
            raise Exception("Sequence length of peptides and binders must be equal")
        np_ss = np.zeros(shape=(len(self.peptides), len(self.cluster_keys)))
        for m in range(len(self.peptides)):
            for i, key in enumerate(self.cluster_keys):
                total_score = 0
                for l in range(self.length):
                    total_score += self.total_scores[key][self.peptides[m][l]][l]
                np_ss[m][i] = total_score
            if m % 500 == 0: print(m / len(self.peptides))
        similarity_scores = pd.DataFrame(np_ss, index = self.peptides, columns = self.cluster_keys)
        self.tss_df = similarity_scores
        return similarity_scores
    
    def lin_reg_predict(path, TSS_path):
        Y = pd.read_csv(path)
        if "Unnamed: 0" in list(Y.columns):
            Y = Y.set_index("Unnamed: 0")
        X = pd.read_csv(TSS_path)
        if "Unnamed: 0" in list(X.columns):
            X = X.set_index("Unnamed: 0")
        scaler = MinMaxScaler(feature_range=(-1,1),copy=True)
        X = pd.DataFrame(scaler.fit_transform(X, [0,1]), index = X.index, columns = X.columns)
        Y.set_index('AA_seq',inplace=True)
        reg = LinearRegression().fit(X, Y)
        prediction = reg.predict(X)
        X['prediction'] = prediction
        data = np.zeros([1992455, 2])
        data[:,0] = Y['Survive3 ']
        data[:,1] = X['prediction']
        score = np.corrcoef(data[:,0], data[:,1])[0, 1]
        predictions = pd.DataFrame(data, index = X.index, columns = ['Survive3', 'Predicted'])
        return predictions, score
    
if __name__ == "__main__":
     ac = AlignmentCalculator()
     ac.import_TSS("../data/set_2_exp/TSS_scores_80p_pep_100000_bind.csv")
     ac.set_binders("../data/set_2_exp/top_binders_rand_100000_2.csv")
     result = ac.lin_reg_predict("../data/set_2_exp/rand_80_survives.csv")
     
#    ex_pep = "../data/set_3_exp/top_peptides_rand_80p.csv"
#    ex_bin = "../data/set_3_exp/top_binders_rand_100000.csv"
#    bind = pd.read_csv(ex_bin)
#    pep = pd.read_csv(ex_pep)
#    ac = AlignmentCalculator(ex_pep, ex_bin)
#    out = ac.calculate_TSS()
#    out.to_csv("../data/set_3_exp/TSS_scores_0p_pep_100000_bind_s3.csv")