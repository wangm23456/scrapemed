"""
Module for building PMC paper datasets, known as paperSets.

Functions for embeddings, natural language search, storage optimization, persistence.
"""
import scrapemed._parse as parse
import scrapemed.scrape as scrape
from scrapemed.paper import Paper
import lxml.etree as ET
import pandas as pd
from typing import Union, List, Dict
import re
import warnings
import matplotlib.pyplot as plt
from wordcloud import WordCloud

class paperSet:
    def __init__(self, papers:List[Paper]):
        """
        Initalize a paperSet. Usually called via paperSet.from_search() or paperSet.from_pmcid_list().
        """
        self.papers = []
        for paper in papers:
            if paper:
                self.papers.append(paper)

        # Make a df of the papers
        paper_series_list = [paper.to_relational() for paper in self.papers]
        self.df = pd.DataFrame(paper_series_list)

        self.index = 0

        print("Done generating paperSet!")

        return None

    @classmethod
    def from_search(cls, email:str, term:str, retmax:int = 10, verbose:bool = False, suppress_warnings:bool = True, suppress_errors:bool = True):
        """Generate a paperSet via a PMC search.

        [email] - use your email to auth with PMC
        [term] - search term
        [retmax] - max number of PMCIDs to return
        [suppress_warnings] - Whether to suppress warnings while parsing XML.
            Note: Warnings are frequent, because of the variable nature of PMC XML data.
            Recommended to suppress when parsing many XMLs at once.
        [suppress_errors] - Return None on failed XML parsing, instead of raising an error. (HIGHLY RECOMMENDED FOR LARGE SEARCHES)
        """
        print("Generating paperSet from search (This can take a while due to PMC HTTP Request Limitations!)...")
        pmcid_list = scrape.search_pmc(email=email, term=term, retmax=retmax, verbose=verbose)['IdList']
        paper_list = [Paper.from_pmc(pmcid, email=email, verbose=verbose, suppress_warnings=suppress_warnings, suppress_errors=suppress_errors) for pmcid in pmcid_list]

        return cls(papers=paper_list)

    @classmethod
    def from_pmcid_list(cls, pmcids:List[int], email:str, download:bool = False, validate:bool = True, strip_text_styling:bool = True, verbose:bool = False, suppress_warnings:bool = True, suppress_errors:bool = True):
        """Generate a paperSet via a list of PMCIDs

        [pmcids] - list of PMCIDs to populate the paperSet
        [email] - use your email to auth with PMC
        [download] - whether or not to download the XMLs corresponding to pmcids
        [validate] - whether or not to validate the XMLs corresponding to pmcids (HIGHLY RECOMMENDED)
        [strip_text_styling] - whether or not to clean common HTML and other text styling out of the XMLs (HIGHLY RECOMMENDED)
        [suppress_warnings] - Whether to suppress warnings while parsing XML.
            Note: Warnings are frequent, because of the variable nature of PMC XML data.
            Recommended to suppress when parsing many XMLs at once.
        [suppress_errors] - Return None on failed XML parsing, instead of raising an error.  (HIGHLY RECOMMENDED FOR LARGE PMCID LISTS)
        """
        print("Generating paperSet from PMCID list (This can take a while due to PMC HTTP Request Limitations!)...")

        xml_list = scrape.get_xmls(pmcids=pmcids, email=email, download=download, validate=validate, strip_text_styling=strip_text_styling, verbose=verbose)
        paper_list = [Paper.from_xml(pmcid, xml_root, verbose=verbose, suppress_warnings=suppress_warnings, suppress_errors=suppress_errors) for pmcid, xml_root in zip(pmcids, xml_list)]
        return cls(papers=paper_list)

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < len(self.papers):
            result = self.papers[self.index]
            self.index += 1
            return result
        else:
            raise StopIteration

    def __len__(self):
        return len(self.papers)

    def __getitem__(self, index):
        if 0 <= index < len(self.papers):
            return self.papers[index]
        else:
            raise IndexError("Index out of range")

    def to_df(self):
        """
        Return a pandas DataFrame representation of the paperSet.
        """
        return self.df

    def add_paper(self, paper:Paper):
        """
        Add Paper to the paperSet directly. Returns True of paper added, False, if the paper was already found in the paperSet.
        Note that papers can easily end up duplicated in the paperSet if they were downloaded different dates or PMCIDs were corrupted.
        """
        if not paper in self.papers:  #caution: comparison of papers is sketchy! Be careful to not duplicate papers in your paperSet
            self.papers.append(paper)
            new_row = paper.to_relational()
            self.df = pd.concat([self.df, new_row.to_frame().T], ignore_index=True)
            return True
        print (f"Paper with pmcid={paper.pmcid} already in paperSet.papers.")
        return False

    def add_papers(self, papers:List[Paper]):
        """
        Add Papers to the paperSet directly. Returns number of papers added.
        """
        count_added = 0
        for paper in papers:
            if self.add_paper(paper):
                count_added += 1
        return count_added

    def add_pmcid(self, pmcid:Union[int, str], email:str, download:bool = False, validate:bool = True, strip_text_styling:bool = True, verbose:bool = False, suppress_warnings:bool = True, suppress_errors:bool = True):
        """
        Add a Paper to the paperSet via PMCID. Returns True if added, False if Paper already in paperSet.

        [pmcid] - PMCID to generate the Paper to add
        [email] - use your email to auth with PMC
        [download] - whether or not to download the XMLs corresponding to pmcid
        [validate] - whether or not to validate the XMLs corresponding to pmcid (HIGHLY RECOMMENDED)
        [strip_text_styling] - whether or not to clean common HTML and other text styling out of the XML (HIGHLY RECOMMENDED)
        [suppress_warnings] - Whether to suppress warnings while parsing XML.
            Note: Warnings are frequent, because of the variable nature of PMC XML data.
            Recommended to suppress when parsing many XMLs at once.
        [suppress_errors] - Return None on failed XML parsing, instead of raising an error.
        """
        paper = Paper.from_pmc(pmcid, email, download=download, validate=validate, verbose=verbose, suppress_warnings=suppress_warnings, suppress_errors=suppress_errors)
        return self.add_paper(paper)

    def add_pmcids(self, pmcids:List[Union[int,str]], email:str, download:bool = False, validate:bool = True, strip_text_styling:bool = True, verbose:bool = False, suppress_warnings:bool = True, suppress_errors:bool = True):
        """Add Papers to the paperSet via a list of PMCIDs. Returns number of papers added.

        [pmcids] - list of PMCIDs to populate the paperSet
        [email] - use your email to auth with PMC
        [download] - whether or not to download the XMLs corresponding to pmcids
        [validate] - whether or not to validate the XMLs corresponding to pmcids (HIGHLY RECOMMENDED)
        [strip_text_styling] - whether or not to clean common HTML and other text styling out of the XMLs (HIGHLY RECOMMENDED)
        [suppress_warnings] - Whether to suppress warnings while parsing XML.
            Note: Warnings are frequent, because of the variable nature of PMC XML data.
            Recommended to suppress when parsing many XMLs at once.
        [suppress_errors] - Return None on failed XML parsing, instead of raising an error.  (HIGHLY RECOMMENDED FOR LARGE PMCID LISTS)
        """
        count_added = 0
        for pmcid in pmcids:
            if self.add_pmcid(pmcid, email, download=download, validate=validate, verbose=verbose, suppress_warnings=suppress_warnings, suppress_errors=suppress_errors):
                count_added += 1
        return count_added

    def visualize(self):
        """
        Generates a general visualization of the paperSet, including unique value visualization
        and a wordcloud for all of the Paper titles.
        """
        self.visualize_unique_values()
        self.visualize_title_wordcloud()

        return None

    def visualize_unique_values(self, columns_to_visualize= ['Last_Updated', 'Journal_Title'])->None:
        for column in columns_to_visualize:
            if column not in self.df.columns:
                print(f"Column '{column}' not found in paperSet.df.")
                continue

            unique_values = self.df[column].unique()
            value_counts = self.df[column].value_counts()

            if len(unique_values) <= 20:
                # Create a pie chart for columns with a small number of unique values
                plt.figure(figsize=(6, 6))
                plt.pie(value_counts, labels=value_counts.index, autopct='%1.1f%%')
                plt.title(f'Pie Chart for {column}')
                plt.show()
            else:
                # Create a histogram for columns with many unique values
                plt.figure(figsize=(10, 6))
                plt.hist(self.df[column], bins=20, edgecolor='k')
                plt.title(f'Histogram for {column}')
                #can add labels, but is very messy
                #plt.xlabel(column)
                plt.ylabel('Frequency')
                plt.show()

        return None

    def visualize_title_wordcloud(self)->None:
        """
        Visualize a wordcloud of all the Paper titles in the paperSet
        """

        titles = [p.title for p in self.papers]
        text = " ".join(titles)

        # Create a WordCloud object
        wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)

        # Display the word cloud using matplotlib
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.title("Wordcloud of Paper Titles", fontsize=16)
        plt.show()

        return None

    #TODO: Add deletion methods if requested by ScrapeMed users.

