import os
from rdkit import Chem
from rdkit.Chem import AllChem
import numpy as np
from rdkit.Chem import MACCSkeys
import pybel
import pandas as pd
import argparse
from mordred import Calculator, descriptors




def process_receptor(drug_db_path,feature="both",descriptor_file="none"):

    df = pd.read_csv(drug_db_path, sep=',')
    df_descriptor_file = pd.read_csv(descriptor_file, sep="\t")

    smiles=df.columns[0]
    receptors = df.columns[1:]
    smiles_records=df[smiles]

    discriptor_keys = list(Calculator(descriptors, ignore_3D=True)._name_dict.keys())
    calc = Calculator(descriptors, ignore_3D=True)
    _canonical_smile_arr = []

    _smile_arr = []

    _ecfp2_512_arr = []
    _ecfp4_512_arr = []
    _ecfp6_512_arr = []
    _ecfp2_2048_arr = []
    _ecfp4_2048_arr = []
    _ecfp6_2048_arr = []

    _maccs_key_arr = []
    _descriptor_arr = []
    _canonical_failure = []
    _len = []
    _progress = []
    _dock_score_index=[]

    counter = -1


    for i in range(len(smiles_records)):
        counter=counter+1


        try:
            canonical_smile=pybel.readstring("smi", smiles_records[i]).write("can").strip()

        except Exception as e:
            print("warning fail in processing(skip) smile:",smiles_records[i],", error msg:",e)
            _canonical_failure.append(smiles_records[i])
            continue

        if feature == "both" or feature == "fingerprint":
            try:
                maccs_key = np.array(MACCSkeys.GenMACCSKeys(Chem.MolFromSmiles(canonical_smile))).tolist()

            except Exception as e:
                print("warning fail in processing(skip) maccs:", smiles_records[i], ", error msg:", e, "receptor:")
                continue
            try:
                m1 = Chem.MolFromSmiles(canonical_smile)
                # ecfp2
                ecfp2_2048 = np.array(AllChem.GetMorganFingerprintAsBitVect(m1, 1, nBits=2048)).tolist()
                ecfp2_512 = np.array(AllChem.GetMorganFingerprintAsBitVect(m1, 1, nBits=512)).tolist()
                # ecfp4
                ecfp4_2048 = np.array(AllChem.GetMorganFingerprintAsBitVect(m1, 2, nBits=2048)).tolist()
                ecfp4_512 = np.array(AllChem.GetMorganFingerprintAsBitVect(m1, 2, nBits=512)).tolist()
                # ecfp6
                ecfp6_2048 = np.array(AllChem.GetMorganFingerprintAsBitVect(m1, 3, nBits=2048)).tolist()
                ecfp6_512 = np.array(AllChem.GetMorganFingerprintAsBitVect(m1, 3, nBits=512)).tolist()
                # scaffold
            except Exception as e:
                print("warning fail in processing(skip) edfp:", smiles_records[i], ", error msg:", e)
                continue

        if feature == "both" or feature == "descriptor":
            if descriptor_file!="none":
                #O=C(Cc1csc(n1)c1ccccc1)NCc1cn(nc1c1ccccc1)Cc1ccccc1
                descriptor =df_descriptor_file.loc[df_descriptor_file["canonical_smile"]==canonical_smile]
                descriptor=pd.DataFrame(descriptor).values.flatten()
                descriptor=descriptor[2:]

                if len(descriptor)== 0:
                    descriptor = calc(Chem.MolFromSmiles(canonical_smile))
                    descriptor=descriptor.fill_missing("nan")
            else:
                try:

                    descriptor = calc(Chem.MolFromSmiles(canonical_smile))
                    descriptor=descriptor.fill_missing("nan")

                except Exception as e:
                    print("warning fail in descriptor(skip)", smiles_records[i], ", error msg:", e)
                    continue

        _canonical_smile_arr.append(canonical_smile)
        _smile_arr.append(smiles_records[i])
        _dock_score_index.append(counter)

        if feature == "both" or feature == "fingerprint":
            _maccs_key_arr.append(maccs_key)
            _ecfp2_2048_arr.append(ecfp2_2048)
            _ecfp4_2048_arr.append(ecfp4_2048)
            _ecfp6_2048_arr.append(ecfp6_2048)
            _ecfp2_512_arr.append(ecfp2_512)
            _ecfp4_512_arr.append(ecfp4_512)
            _ecfp6_512_arr.append(ecfp6_512)

        if feature =="both" or feature == "descriptor":
            _descriptor_arr.append(descriptor)

        if counter%100==0:
            _len.append(len(smiles_records))
            _progress.append(counter)
            progress = {"total": _len, "processed": _progress}
            df_p = pd.DataFrame(progress)
            df_p.to_csv("progress.csv", sep='\t', index=False)
            print("size:",len(smiles_records),"processing counter: ",counter)


    data_failed = {"smile":_canonical_failure}

    df_out_2 = pd.DataFrame(data_failed)
    df_out_2.to_csv("canonical_fail_smile.csv", sep='\t', index=False)

    for receptor in receptors:
        receptor_dock_score=df[receptor]
        _dock_score_arr=receptor_dock_score[_dock_score_index]

        data_desc = {"canonical_smile": _canonical_smile_arr, "smile": _smile_arr, "dock_score": _dock_score_arr}

        data_fp = {"canonical_smile": _canonical_smile_arr, "smile": _smile_arr, "dock_score": _dock_score_arr,
                   "maccs_key": _maccs_key_arr,
                   "ecfp2_512": _ecfp2_512_arr, "ecfp4_512": _ecfp4_512_arr, "ecfp6_512": _ecfp6_512_arr,
                   "ecfp2_2048": _ecfp2_2048_arr, "ecfp4_2048": _ecfp4_2048_arr, "ecfp6_2048": _ecfp6_2048_arr}
        try:

            if feature == "both" or feature == "fingerprint":
                df_out = pd.DataFrame(data_fp)
                df_out.to_csv(receptor + "_ena+db_fingerprints.csv", sep='\t', index=False)

            if feature == "both" or feature == "descriptor":
                df_header = pd.DataFrame(data_desc)
                discriptor_out = pd.DataFrame(_descriptor_arr, columns=discriptor_keys)
                df_dec = pd.concat([df_header, discriptor_out], axis=1)
                df_dec.to_csv(receptor + "_ena+db_descriptors.csv", sep='\t', index=False)

            print(receptor, " is completed")

        except Exception as e:
            print(e)


#drug_db_path
#input file should use , as seperator and have the followng format
#smiles,receptor1_docking_score,receptor2_docking_score ...
#OC(=O)C(=O)C,0,1,1.2

#descriptor_file
#has following format, sep tab
#canonical_smile	ID	descriptor1 descriptor2 ...
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-feature', default="both", type=str, help='feature to process',
                        choices=["both", "fingerprint", "descriptor"])
    parser.add_argument('-file', default="docking_data_out_v3.1.200.csv", type=str, help='docking_data_out_vx.x.x.csv file')
    parser.add_argument('-descriptor_file', default="descriptors_clean_out.csv", type=str, help='xxx.descriptors_clean_out.csv file')


    try:
        args = parser.parse_args()
    except Exception as e:
        print(e)
        exit()

    print(args)
    return args


if __name__ == '__main__':

    try:
        args = get_args()
    except Exception as e:
        print("fetch input failure:",e)
        exit()

    feature = args.feature
    drug_db_path = args.file
    descriptor_file = args.descriptor_file

    process_receptor(drug_db_path,feature,descriptor_file)


