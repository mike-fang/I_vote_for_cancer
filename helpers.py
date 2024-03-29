# helper functions for dealing with text

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import KFold, cross_val_score
from sklearn.metrics import log_loss
from sklearn.preprocessing import LabelBinarizer

def get_unique_text(variants_df, text_df, cls, save = None, suppress_output = True):
    """
    Takes pandas DataFrames for variants and text files. The
    class number should be an int corresponding to the tumor
    class. Returns a string with all of the unique text
    corresponding to cls.

    suppress_output suppresses printing additional information
    """

    matching_ids_df = variants_df.loc[variants_df['Class'] == cls]['ID'] # all IDs matching cls
    class_text_df = text_df.loc[text_df['ID'].isin(matching_ids_df)]
    # class_text_df is all the text pertaining to cls (including duplicates)
    unique_text = class_text_df['Text'].unique()
    unique_text_string = '\n'.join(unique_text)

    if not suppress_output:
        cls_size = class_text_df.size
        unique_size = unique_text.shape[0]
        print('Number of entries in class {}: {}'.format(cls, cls_size))
        print('Number of unique texts: {}'.format(unique_size))

    if save is not None:
        print('Saving to file: {}'.format(save))
        f = open(save, 'wt')
        f.write(unique_text_string)
        f.close()

    return unique_text_string

def get_number_instances(docs, vocabulary):
    """
    docs: list of strings
    vocabulary: list of strings

    Returns a numpy array which vectorizes the
    documents according to the number of instances
    of terms in the vocabulary.
    Each -row- of the returned array corresponds
    to a document vector. e.g. to get the
    document vector for document 3, use
    x[3,:]
    """

    cv = CountVectorizer(vocabulary=vocabulary)
    x = cv.fit_transform(docs).toarray()
    return x

def train_test_split(train_variation_file, train_text_file):
    """
    This function takes the variants and text file and splits them into 80% for training and 20% 
    for testing in a stratifiled way according to classes, and returns four DataFrames:
    text_train, text_test, variants_train, variants_test
    """
    from sklearn.model_selection import train_test_split
    import pandas as pd
    y = pd.read_csv(train_variation_file)
    X = pd.read_csv(train_text_file, sep="\|\|", engine="python", skiprows=1, names=["ID", "Text"])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y.Class)
    return X_train, X_test, y_train, y_test

def plot_roc_curve(y_test, y_score):
    """plot ROC curves and calculate AUC for multiclass classification,
    given y_test(true) and y_score(predicted) of dimension[#samples, #classes]"""
    import numpy as np
    import matplotlib.pyplot as plt
    from itertools import cycle
    from sklearn.metrics import roc_curve, auc
    from scipy import interp
    
    n_classes = y_test.shape[1]
    
    # Compute ROC curve and ROC area for each class
    fpr = dict()
    tpr = dict()
    roc_auc = dict()
    for i in range(n_classes):
        fpr[i], tpr[i], _ = roc_curve(y_test[:, i], y_score[:, i])
        roc_auc[i] = auc(fpr[i], tpr[i])

    # Compute micro-average ROC curve and ROC area
    fpr["micro"], tpr["micro"], _ = roc_curve(y_test.ravel(), y_score.ravel())
    roc_auc["micro"] = auc(fpr["micro"], tpr["micro"])

    # Compute macro-average ROC curve and ROC area

    # First aggregate all false positive rates
    all_fpr = np.unique(np.concatenate([fpr[i] for i in range(n_classes)]))

    # Then interpolate all ROC curves at this points
    mean_tpr = np.zeros_like(all_fpr)
    for i in range(n_classes):
        mean_tpr += interp(all_fpr, fpr[i], tpr[i])

    # Finally average it and compute AUC
    mean_tpr /= n_classes

    fpr["macro"] = all_fpr
    tpr["macro"] = mean_tpr
    roc_auc["macro"] = auc(fpr["macro"], tpr["macro"])

    # Plot all ROC curves
    plt.figure()
    plt.plot(fpr["micro"], tpr["micro"],
             label='micro-average ROC curve (area = {0:0.2f})'
                   ''.format(roc_auc["micro"]),
             color='deeppink', linestyle=':', linewidth=4)

    plt.plot(fpr["macro"], tpr["macro"],
             label='macro-average ROC curve (area = {0:0.2f})'
                   ''.format(roc_auc["macro"]),
             color='navy', linestyle=':', linewidth=4)
    
    lw=2
    colors = cycle(['aqua', 'darkorange', 'cornflowerblue'])
    for i, color in zip(range(n_classes), colors):
        plt.plot(fpr[i], tpr[i], color=color, lw=lw,
                 label='ROC curve of class {0} (area = {1:0.2f})'
                 ''.format(i, roc_auc[i]))

    plt.plot([0, 1], [0, 1], 'k--', lw=lw)
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Some extension of Receiver operating characteristic to multi-class')
    plt.legend(loc="lower right")
    plt.show()

def get_training(train_variation_file, train_text_file):
    """
    use this to get 80% data from training_variants and training_text 
    to use for training
    """
    import pandas as pd
    train = list(pd.read_csv('./train_index',names = ['ID','ID2'])['ID'])
    y = pd.read_csv(train_variation_file)
    X = pd.read_csv(train_text_file, sep="\|\|", engine="python", skiprows=1, names=["ID", "Text"])
    return X.iloc[train, :], y.iloc[train, :]

def get_test(train_variation_file, train_text_file):
    """
    use this to get 20% data from training_variants and training_text 
    for reporting final score, don't use it for model selection or parameter tuning
    """
    import pandas as pd
    test = list(pd.read_csv('./test_index',names = ['ID','ID2'])['ID'])
    y = pd.read_csv(train_variation_file)
    X = pd.read_csv(train_text_file, sep="\|\|", engine="python", skiprows=1, names=["ID", "Text"])
    return X.iloc[test, :], y.iloc[test, :]

def kfold_score(clf, X,y, splits=3):
    '''
    clf is the classifier. X is all the training data,
    y is the labels. Returns average log-loss over
    the k folds
    '''
    lb = LabelBinarizer()
    lb.fit(y)
    k_fold = KFold(n_splits=splits)
    values = []
    for train, test in k_fold.split(X):
        clf.fit(X[train], y[train])
        y_test_prob = clf.predict_proba(X[test])
        y_true = lb.transform(y[test])
        values.append(log_loss(y_true, y_test_prob))
    return np.mean(values)

def submission(filename, prob_matrix):
    """
    filename: location of csv file
    prob_matrix: matrix of dimension(n_sample, n_class)
    """
    with open(filename, 'w') as f:
        f.write('ID,class1,class2,class3,class4,class5,class6,class7,class8,class9\n')
        for i in range(prob_matrix.shape[0]):
            f.write(str(i)+',')
            for j in range(prob_matrix.shape[1]):
                f.write(str(prob_matrix[i][j]))
                if j<8:
                    f.write(',')
            f.write('\n')

def get_full_table(variants_file, text_file):
	"""create full table from text and variantes"""

	variants = pd.read_csv(variants_file)
	text = pd.read_csv(text_file, sep="\|\|", engine="python", skiprows=1, names=["ID", "Text"])
	data_full = variants.merge(text, how='inner', on='ID')
	return data_full


    
