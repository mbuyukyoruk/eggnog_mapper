import argparse
import sys
import os
import subprocess
import textwrap
import pandas as pd

try:
    from Bio import SeqIO
except:
    print("SeqIO module is not installed! Please install SeqIO and try again.")
    sys.exit()

try:
    import tqdm
except:
    print("tqdm module is not installed! Please install tqdm and try again.")
    sys.exit()

parser = argparse.ArgumentParser(prog='python eggnog_mapper.py',
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=textwrap.dedent('''\
# eggnog_mapper

Author: Murat Buyukyoruk

        eggnog_mapper help:

This script is developed to generate a dataframe from eggnog-mapper neighbourhood analysis (eggnog_mapper.py) that can be used to create alignment panel with phylogenetic trees (i.e., to use with Pylo2genemap script). tqdm is required to provide a progress bar.

Syntax:

        python eggnog_mapper.py -i demo.fasta -d demo_eggnog_annotations.txt -g COG -o out.txt -f 5

        OR

        python eggnog_mapper.py -i demo.fasta -d demo_eggnog_annotations.txt -g PFAM -o out.txt -f 0

eggnog_mapper dependencies:

Bio module and SeqIO available in this package          refer to https://biopython.org/wiki/Download

tqdm                                                    refer to https://pypi.org/project/tqdm/

pandas                                                  refer t0 https://pypi.org/project/pandas/

Input Paramaters (REQUIRED):
----------------------------
	-i/--input		FASTA			                Specify a fasta file used for e_mapper.py. FASTA file requires headers starting with accession number.

	-o/--output		Output file	                    Specify a output file name that should contain genemap info generated by eggnog_mapper annotations file.

	-d/--data		HMMER domtblout		            Specify a eggnog_mapper annotations file.

Parameters [optional]:
----------------------

	-g/--gene	    COG, COG_Category or PFAM		Specify type of gene is reported (i.e., COG, COG_Category, PFAM) (default: COG)

	-f/--filter 	Number   		                Specify a number for reporting clusters. For example use number 5 to show COG annotation with more than 5 occurences. use 1 to show all COG annotations. (default: 5)

Basic Options:
--------------
	-h/--help		HELP			                Shows this help text and exits the run.

      	'''))
parser.add_argument('-i', '--input', required=True, type=str, dest='filename',
                    help='Specify a original fasta file.\n')
parser.add_argument('-d', '--data', required=True, type=str, dest='data',
                    help='Specify eggnog annotations data file.\n')
parser.add_argument('-o', '--output', required=True, dest='out',
                    help='Specify a output file name.\n')
parser.add_argument('-g', '--gene_type', required=False, dest='gene_type', default="COG",
                    help='Specify type of gene is reported (i.e., COG, COG_Category, PFAM).\n')
parser.add_argument('-f', '--filter', required=False, dest='filter_num', default=5, type=int,
                    help='Specify filter cutoff to show cluster more than the selected threshold (i.e., 5 for showing clusters contains more than five sequences).\n')

results = parser.parse_args()
filename = results.filename
data = results.data
out = results.out
gene_type = results.gene_type
filter_num = results.filter_num

os.system('> ' + out)

seq_id = []
seq_start = []
seq_end = []
seq_strand = []

molecule_list =[]
ORF_list = []
genome_list =[]

proc = subprocess.Popen("grep -c '>' " + filename, shell=True, stdout=subprocess.PIPE,text=True )
length_seq = int(proc.communicate()[0].split('\n')[0])

with tqdm.tqdm(range(length_seq + 1)) as pbar:
    pbar.set_description('Getting sequence info...')
    for record in SeqIO.parse(filename, "fasta"):
        pbar.update()
        acc = record.id
        ORF = acc.split("|")[0]
        molecule = acc.split("|")[1]
        genome_acc = molecule.rsplit("_", 1)[0]
        start = int(record.description.split(" # ")[1])
        stop = int(record.description.split(" # ")[2])
        strand = str(record.description.split(" # ")[3]).replace("-1", "0")
        seq_id.append(acc)
        seq_start.append(start)
        seq_end.append(stop)
        seq_strand.append(strand)
        molecule_list.append(molecule)
        ORF_list.append(ORF)
        genome_list.append(genome_acc)

df = pd.DataFrame(columns=['molecule', 'ORF', 'genome',"gene","start","end","orientation"])

proc = subprocess.Popen("wc -l < " + data, shell=True, stdout=subprocess.PIPE, text=True)
length = int(proc.communicate()[0].split('\n')[0])

with tqdm.tqdm(range(length + 1)) as pbar:
    pbar.set_description('Adding EggNOG annotation data... ')
    with open(data, "r") as file:
        i=0
        for line in file:
            pbar.update()
            if line[0] != "#":
                arr = line.split('\t')
                accession_comb = arr[0]
                ORF = accession_comb.split("|")[0]
                molecule = accession_comb.split("|")[1]
                genome_acc = molecule.rsplit("_", 1)[0]

                if gene_type.lower() == "cog":
                    gene = arr[4].split("@")[0]
                elif gene_type.lower() == "cog_category":
                    gene = arr[6]
                elif gene_type.lower() == "pfam":
                    gene = arr[-1]
                else:
                    print("Invalid option for data type argument. Use 'COG', 'COG_Category' or 'PFAM' options.")
                    sys.exit()

                ind = seq_id.index(accession_comb)

                start = str(seq_start[ind])
                end = str(seq_end[ind])
                gene_strand = str(seq_strand[ind]).replace("-1", "0")

                df.loc[i] = [molecule,ORF,genome_acc,gene,start,end,gene_strand]

                if ORF == molecule:
                    i += 1
                    df.loc[i] = [molecule, ORF, genome_acc, "Anchor", start, end, gene_strand]

                i+=1

dict = {'molecule': molecule_list,'ORF': ORF_list,'genome': genome_list,'gene': 'no-hit','start': seq_start,'end': seq_end,'orientation': seq_strand}
df_all = pd.DataFrame(dict, columns=['molecule', 'ORF', 'genome',"gene","start","end","orientation"])

df = df._append(df_all[~df_all.ORF.isin(df.ORF.values)], ignore_index=True)

df['frequency'] = df['gene'].map(df['gene'].value_counts())
df.loc[df['frequency'] <= filter_num, 'gene'] = "Other"
df = df.drop(columns=['frequency'])

df.to_csv(out, sep='\t', index=False, header=True)

