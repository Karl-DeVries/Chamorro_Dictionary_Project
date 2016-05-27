#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''This module contains functions used for loading and searching the Chamorro dictionary.
It can also be invoked from the commandline as a script that searches the dictionary. 

Usage:

    To search for QUERY via the commandline from the containing directory use the following command: 

        python chamorroSearch.py -s QUERY
    
    It can also be invoked to run a little demo:
    
        python chamorroSearch.py -d

Dependencies:

    This script depends on two external json files which should be available in the same 
    directory as the script: 

        ./ChamorroVariants.json 

        ./ChamorroDictionary.json
    
    ChamorroVariants.json contains for each dictionary entry a list of known spelling variants 
    that have been recovered from the dictionary itself. 

    ChamorroDictionary.json contains the dictionary itself.     

Search Proceedure:

    The search uses a modified ratio test to compare entries to the query.   
    
Ratio Test:

    The ratio test provides a match-score between 0 and 1 for each pair  of strings. The score is 
    determined by taking the longest common subsequence between the two strings, multiplying it by
    two and dividing by the sum of the lengths. Thus two identical strings will have a score of 1. 
    Two strings that share no common subsequence will have a score of 0.
    
    The ratio test is was originally devised as a method of string matching that provided results 
    that "looked right" to people. 
    
    With some testing it was determined that the ratio test provides closer matches than bi/tri-gram
    vector models or string edit distance. But further testing may be needed.
    
    We have implemented a modified version of the ratio test that takes into account how compressed
    The lcs is inside the query.  
    
Modules:

    The code relies on the several default python moduals:
    
        json: used for loading java script objects. 
    
        os: manages opening and closing files.
    
        sys: manages input from the commandline.
    
        re: impilements regular expressions.
    
        difflib: implements a number of sequence matching algorithms.

            The script only imports the SequenceMatcher object which contains the .ratio() method 
            which implements the ratio test. 
    
        collections: provides a number of useful containers.

            The script only imports the Counter object which is a beefed up default dictionary 
            that maps keys to numbers. It provides keys with a default value of 0. The useful 
            method is the .most_common(n) method which returns a list of n keys in with decreasing
            values. 

Documentation:

    Documentation can be regenerated useing pydoc. From the directory containing the script call from
    the terminal the command:
    
    python -m pydoc -w chamorroSearch 

ToDo:
    (i)  Try smarter rankings of the search terms
    (ii) Provide a way of specifying number of desired entries from the command line
'''


###########
# Imports #
###########

import json, os, sys, re
from optparse import OptionParser
from difflib import SequenceMatcher
from collections import Counter

reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

#################################
# Functions for Loading Objects #
#################################

def loadVariants(path = "./ChamorroVariants.json"):
    '''Loads the dictionary of variant spellings.
    
    Args: 
        path: the path to the ChamorroVariants.json dictionary
            Defults to the current directory.
    
    Returns: the variants dictionary.
    '''
    f = open(path, "r")
    variants = json.load(f)
    f.close()    
    return variants

def loadDictionary(path = "./ChamorroDictionary.json"):
    '''Loads the dictionary of variant spellings.
    
    Args: 
        path: the path to the ChamorroDictionary.json
            dictionary. Defaults to the current directory. 
    
    Returns: the Chamorro Dictionary
    '''
    f = open(path, "r")
    dictionary = json.load(f)
    f.close()
    return dictionary

##########################
# Some String Processing #
##########################

def preProcess(word):
    '''Regularizes queries.
    
    Ensures that the query is a unicode string, 
    regularizes glottal stops, removes stress 
    marking diacritics, and lower cases the input.
    Note that this preprocessing leaves more intact
    than its older counterpart.
    
    Args: 
        word: a query to be sanitized.
    
    Returns: 
        a unicode string for further processing.
    '''
    word = unicode(word.lower()) 
    substitutions = [
             (u"’", u"'"), #regularize '
    		 (u"é", u"e"), # get rid of stress marking diacritics
             (u"í", u"i"),
			 (u"ó", u"o"),
			 (u"ú", u"u"),
			 (u"á", u"a"),
			 (u"Ñ", u"ñ")
    		]
    for (find, replace) in substitutions:
        word = word.replace(find, replace)	
    return word

#The next function does a very very simple striping, it takes off the
#most common affixes
def simpleStrip(word):
    '''Takes off a few common affixes
    '''
    parts = word.split("-") 
    word = parts[0]
    prefixes =  [r"^ma", r"^fa", r"^um"]
    for pref in prefixes:
        match = re.search(pref, word)
        if match:
            word = re.sub(pref, "", word) 
    return word
    

#########################
# Fuzzy String Matching #
#########################

def bestRatio(wordList1, wordList2):
    '''Reports the match score for two lists of words
    
    Takes two lists of words and reports the score associated with
    the highest scoring pair from the two lists. The scoring uses a 
    sequence matcher object from difflib that implements the ratio score.
    The ratio score is defined as two times the longest common subsequence
    between w1 and w2 divided by the sum of the lengths of w1 and w2. 
    
    Args:
        wordList1: a list of strings
        wordList2: a list of strings
    
    Returns: a float representing the best mathc score
    '''
    #initilize the ratio score at 0.0
    ratio = 0.0 
    #set up the sequence matcher object that implements the ratio test
    s = SequenceMatcher(isjunk = None, autojunk = False) 
    for w1 in wordList1:
        #This is kinda dumb, but this runs faster than setting seq1; the docs on difflib explain
        #that meta-inormation is stored about seq2 that facilitates the sequence test, while
        #no information is stored about seq1. So, if you want to compare one sequence to multiple
        #other sequences it is best to keep resetting seq1.
        s.set_seq2(w1) # set seq2 as w1
        for w2 in wordList2:
            s.set_seq1(w2) # set seq1 as w2 
            r = s.ratio() # get the ratio
            ratio = max(r, ratio) # take the new ratio if its bigger than the previous one
    return ratio

#This function is just a wrapper for the sequence matcher object
def ratioTest(query, inflected):
    m = SequenceMatcher(isjunk = None, autojunk = False)
    m.set_seq1(query)
    m.set_seq2(inflected)
    return m.ratio()

# This calculates the lcs and smallest window for two strings
def lcs_sw(s1, s2):
    '''Finds the length of a longest common subsequence and the length
    of a smallest window that contains a longest common subsequence
    
    The lcs measures how much of s2 and be found inside s1
    The sw measures how spread out the lcs is inside s2
    
    Args:
        s1: the first string
        s2: a second string
    
    Returns:
        length: an int representing the length of the longest common subsequence
        window: an int representing the length of of the smallest window in s1 containing 
                the lcs
    '''
    rows = len(s2) + 1
    columns = len(s1) + 1
    lengths = [[(0, 0, 0)  for j in range(rows)] for i in range(columns)]
    # row 0 and column 0 are initialized to 0 already
    for j, y in enumerate(s2):
        for i, x in enumerate(s1):
            # if the characters match we add on to the diagonal 
            if x == y:
                #If this is the first matching character
                #set the begining to the current index
                if lengths[i][j][0] == 0:
                    b = i
                #Otherwise, set the begining to the previous beginging
                else:
                    b = lengths[i][j][1]
                # increment the length by 1    
                l = lengths[i][j][0] + 1
                #add one to the end index
                e = i + 1
                # check that adjacent sides don't have the same length
                rlen, rb, re = lengths[i+1][j]
                dlen, db, de = lengths[i][j+1]
                if rlen == l or dlen == l:
                    if rlen > dlen:
                        if re - rb < e - b:
                            lengths[i+1][j+1] = (rlen, rb, re)
                        else:
                            lengths[i+1][j+1] = (l, b, e)
                    elif dlen > rlen:
                        if de - db < e - b:
                            lengths[i+1][j+1] = (dlen, db, de)
                        else:
                            lengths[i+1][j+1] = (l, b, e)
                    else: 
                        if re - rb < de - db:
                            lengths[i+1][j+1] = (rlen, rb, re)
                        else:  
                            lengths[i+1][j+1] = (dlen, db, de)
                else:
                    # increment the matrix
                    lengths[i+1][j+1] = (l, b, e)
            # otherwise we take the best from the previous row or column:
            else:
                rlen, rb, re = lengths[i+1][j] 
                dlen, db, de = lengths[i][j+1]
                # We take the cell associated with the longest subsequence if they aren't equal
                if rlen > dlen:
                    lengths[i+1][j+1] = (rlen, rb, re)
                elif dlen > rlen:
                    lengths[i+1][j+1] = (dlen, db, de) 
                # Otherwise we take the cell associated with the shortest window
                else:
                    if re - rb < de - db:
                        lengths[i+1][j+1] = (rlen, rb, re)
                    else:
                        lengths[i+1][j+1] = (dlen, db, de)
    length = lengths[-1][-1][0]
    window = lengths[-1][-1][2] - lengths[-1][-1][1] 
    return length, window
 
# This provides an alternative to the ratio test that penalizes strings that 
# have an lcs that is 'spread out' relative to those that don't    
def spread_RO(s1, s2):
    '''This works very much like the ratio test only
    it penalizes strings more for having a large window
    over which the lcs is distributed.
    
    Args:
        s1, s2: strings
        
    Returns: 
        an int giving a modified ratio score
    '''
    lcs, wl = lcs_sw(s1, s2)
    numerator = float(3 * lcs)
    denominator = float(len(s1) + len(s2) + wl)
    return numerator / denominator


##########################
# Searching and Printing #
##########################

#Here is the new search function, it does not depend on the varients dictionary 
#Nor does it need to do any stripping since in testing the modified ratio score performs
#better than the system with stripping
def search(query, dictionary, n = 5):
    q = preProcess(query)
    matches = {}
    for entry in dictionary.keys():
        k = preProcess(entry)
        matches[entry] = spread_RO(k, q)
    keys = [ r[0] for r in Counter(matches).most_common(n) ] 
    return [ {k : dictionary[k] } for k in keys ]


###############
# Main Script #
###############

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--search", 
                  dest = "query", help = "look up QUERY", metavar = "QUERY", default = "")
    parser.add_option("-d", "--demo",
                  action = "store_true", dest = "demo", default = False,
                  help = "run a demo of the search dictionary")
                  
    (options, args) = parser.parse_args()
        
    # search the dictionary if there is a query
    q = options.query
    if q:
        print "This will search for " + q + " if only you had access to the dictionary"
        
    # run the demo if it was asked for        
    if options.demo:
        print "This would run a quick demo\nInstead lets run a quick test of the lcs_sw algorithm:"
        
        l, w = lcs_sw("abc", "ac")
        
        print "'abc' and 'ac' have a lcs of " + str(l) + ' in a window of ' + str(w)

        l, w = lcs_sw("abbc", "ac") 
        
        print "'abbc' and 'ac' have an lcs of " + str(l) + " in a window of " + str(w)  
        
        l, w = lcs_sw("acabc", "ac") 
        
        print "'acabc' and 'ac' have an lcs of " + str(l) + " in a window of " + str(w)  

        l, w = lcs_sw("abcac", "ac") 
        
        print "'abcac' and 'ac' have an lcs of " + str(l) + " in a window of " + str(w)  
        
        l, w = lcs_sw("abacbc", "ac") 
        
        print "'abacbc' and 'ac' have an lcs of " + str(l) + " in a window of " + str(w)  
        
        l, w = lcs_sw("adbc", "abc") 
        
        print "'adbc' and 'abc' have an lcs of " + str(l) + " in a window of " + str(w)  
