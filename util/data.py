import sys
import os
import pickle
import tarfile

import theano
import numpy as np
from scipy.ndimage import convolve
try:
  from sklearn import datasets
  from sklearn.cross_validation import train_test_split
except ImportError:
  print "Warning: Couldn't load scikit-learn"

# ----------------------------------------------------------------------------

def whiten(X_train, X_valid):
  offset = np.mean(X_train, 0)
  scale = np.std(X_train, 0).clip(min=1)
  X_train = (X_train - offset) / scale
  X_valid = (X_valid - offset) / scale
  return X_train, X_valid

# ----------------------------------------------------------------------------

def load_cifar10():
  """Download and extract the tarball from Alex's website."""
  dest_directory = '.'
  DATA_URL = 'http://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz'
  if not os.path.exists(dest_directory):
    os.makedirs(dest_directory)
  filename = DATA_URL.split('/')[-1]
  filepath = os.path.join(dest_directory, filename)
  if not os.path.exists(filepath):
    if sys.version_info[0] == 2:
      from urllib import urlretrieve
    else:
      from urllib.request import urlretrieve

    def _progress(count, block_size, total_size):
      sys.stdout.write('\r>> Downloading %s %.1f%%' % (filename,
          float(count * block_size) / float(total_size) * 100.0))
      sys.stdout.flush()
    filepath, _ = urlretrieve(DATA_URL, filepath, _progress)
    print()
    statinfo = os.stat(filepath)
    print('Successfully downloaded', filename, statinfo.st_size, 'bytes.')
    tarfile.open(filepath, 'r:gz').extractall(dest_directory)  

  def load_CIFAR_batch(filename):
    """ load single batch of cifar """
    with open(filename, 'rb') as f:
      datadict = pickle.load(f)
      X = datadict['data']
      Y = datadict['labels']
      X = X.reshape(10000, 3, 32, 32).astype("float32")
      Y = np.array(Y, dtype=np.uint8)
      return X, Y

  xs, ys = [], []
  for b in range(1,6):
    f = 'cifar-10-batches-py/data_batch_%d' % b
    X, Y = load_CIFAR_batch(f)
    xs.append(X)
    ys.append(Y)    
  Xtr = np.concatenate(xs)
  Ytr = np.concatenate(ys)
  del X, Y
  Xte, Yte = load_CIFAR_batch('cifar-10-batches-py/test_batch')
  return Xtr, Ytr, Xte, Yte

def load_mnist():
  # We first define a download function, supporting both Python 2 and 3.
  if sys.version_info[0] == 2:
    from urllib import urlretrieve
  else:
    from urllib.request import urlretrieve

  def download(filename, source='http://yann.lecun.com/exdb/mnist/'):
    print "Downloading %s" % filename
    urlretrieve(source + filename, filename)

  # We then define functions for loading MNIST images and labels.
  # For convenience, they also download the requested files if needed.
  import gzip

  def load_mnist_images(filename):
    if not os.path.exists(filename):
      download(filename)
      # Read the inputs in Yann LeCun's binary format.
    with gzip.open(filename, 'rb') as f:
      data = np.frombuffer(f.read(), np.uint8, offset=16)
    # The inputs are vectors now, we reshape them to monochrome 2D images,
    # following the shape convention: (examples, channels, rows, columns)
    data = data.reshape(-1, 1, 28, 28)
    # The inputs come as bytes, we convert them to float32 in range [0,1].
    # (Actually to range [0, 255/256], for compatibility to the version
    # provided at http://deeplearning.net/data/mnist/mnist.pkl.gz.)
    return data / np.float32(256)

  def load_mnist_labels(filename):
    if not os.path.exists(filename):
      download(filename)
      # Read the labels in Yann LeCun's binary format.
    with gzip.open(filename, 'rb') as f:
      data = np.frombuffer(f.read(), np.uint8, offset=8)
    # The labels are vectors of integers now, that's exactly what we want.
    return data

  # We can now download and read the training and test set images and labels.
  X_train = load_mnist_images('train-images-idx3-ubyte.gz')
  y_train = load_mnist_labels('train-labels-idx1-ubyte.gz')
  X_test = load_mnist_images('t10k-images-idx3-ubyte.gz')
  y_test = load_mnist_labels('t10k-labels-idx1-ubyte.gz')

  # We reserve the last 10000 training examples for validation.
  X_train, X_val = X_train[:-10000], X_train[-10000:]
  y_train, y_val = y_train[:-10000], y_train[-10000:]

  # We just return all the arrays in order, as expected in main().
  # (It doesn't matter how we do this as long as we can read them again.)
  return X_train, y_train, X_val, y_val, X_test, y_test

def load_svhn():
  if sys.version_info[0] == 2:
    from urllib import urlretrieve
  else:
    from urllib.request import urlretrieve

  def download(filename, source="https://github.com/smlaine2/tempens/raw/master/data/svhn/"):
    print "Downloading %s" % filename
    urlretrieve(source + filename, filename)

  import cPickle
  def load_svhn_files(filenames):
    if isinstance(filenames, str):
        filenames = [filenames]
    images = []
    labels = []
    for fn in filenames:
        if not os.path.isfile(fn): download(fn)
        with open(fn, 'rb') as f:
          X, y = cPickle.load(f)
        images.append(np.asarray(X, dtype='float32') / np.float32(255))
        labels.append(np.asarray(y, dtype='uint8'))
    return np.concatenate(images), np.concatenate(labels)

  X_train, y_train = load_svhn_files(['train_%d.pkl' % i for i in (1, 2, 3)])
  X_test, y_test = load_svhn_files('test.pkl')

  return X_train, y_train, X_test, y_test

# ----------------------------------------------------------------------------
# other

def split_semisup(X, y, n_lbl):
  n_tot = len(X)
  idx = np.random.permutation(n_tot)
  
  X_lbl = X[idx[:n_lbl]].copy()
  X_unl = X[idx[n_lbl:]].copy()
  y_lbl = y[idx[:n_lbl]].copy()
  y_unl = y[idx[n_lbl:]].copy()

  return X_lbl, y_lbl, X_unl, y_unl

def load_digits():
    digits = datasets.load_digits()
    X = np.asarray(digits.data, 'float32')
    X, Y = nudge_dataset(X, digits.target)
    X = (X - np.min(X, 0)) / (np.max(X, 0) + 0.0001)  # 0-1 scaling
    n, d2 = X.shape
    d = int(np.sqrt(d2))
    X = X.reshape((n,1,d,d))
    Y = np.array(Y, dtype=np.uint8)

    X_train, X_test, Y_train, Y_test = train_test_split(X, Y,
                                                        test_size=0.2,
                                                        random_state=0)
    return X_train, Y_train, X_test, Y_test

def load_noise(n=100,d=5):
  """For debugging"""
  X = np.random.randint(2,size=(n,1,d,d)).astype('float32')
  Y = np.random.randint(2,size=(n,)).astype(np.uint8)

  return X, Y

def load_h5(h5_path):
  """This was untested"""
  import h5py
  # load training data
  with h5py.File(h5_path, 'r') as hf:
    print 'List of arrays in input file:', hf.keys()
    X = np.array(hf.get('data'))
    Y = np.array(hf.get('label'))
    print 'Shape of X: \n', X.shape
    print 'Shape of Y: \n', Y.shape

    return X, Y

def nudge_dataset(X, Y):
    """
    This produces a dataset 5 times bigger than the original one,
    by moving the 8x8 images in X around by 1px to left, right, down, up
    """
    direction_vectors = [
        [[0, 1, 0],
         [0, 0, 0],
         [0, 0, 0]],

        [[0, 0, 0],
         [1, 0, 0],
         [0, 0, 0]],

        [[0, 0, 0],
         [0, 0, 1],
         [0, 0, 0]],

        [[0, 0, 0],
         [0, 0, 0],
         [0, 1, 0]]]

    shift = lambda x, w: convolve(x.reshape((8, 8)), mode='constant',
                                  weights=w).ravel()
    X = np.concatenate([X] +
                       [np.apply_along_axis(shift, 1, X, vector)
                        for vector in direction_vectors])
    Y = np.concatenate([Y for _ in range(5)], axis=0)
    return X, Y

def prepare_dataset(X_train, y_train, X_test, y_test, aug_translation=0, zca=False):
  # Whiten input data
  def whiten_norm(x):
    x = x - np.mean(x, axis=(1, 2, 3), keepdims=True)
    x = x / (np.mean(x ** 2, axis=(1, 2, 3), keepdims=True) ** 0.5)
    return x

  if zca:
    # apply whitening
    whitener = ZCA(x=X_train)
    X_train = whitener.apply(X_train)
    X_test = whitener.apply(X_test)

    # normalize data with range
    X_train = whiten_norm(X_train)
    X_test = whiten_norm(X_test)

    # remove outliers
    X_train = np.clip(X_train, -3, 3)
    X_test = np.clip(X_test, -3, 3)  
  else:
    X_train = whiten_norm(X_train)
    X_test = whiten_norm(X_test)


  # Pad according to the amount of jitter we plan to have.

  p = aug_translation
  if p > 0:
      X_train = np.pad(X_train, ((0, 0), (0, 0), (p, p), (p, p)), 'reflect')
      X_test = np.pad(X_test, ((0, 0), (0, 0), (p, p), (p, p)), 'reflect')

  # Random shuffle.
  # indices = np.arange(len(X_train))
  # np.random.shuffle(indices)
  # X_train = X_train[indices]
  # y_train = y_train[indices]

  return X_train, y_train, X_test, y_test

class ZCA(object):
    def __init__(self, regularization=1e-5, x=None):
        self.regularization = regularization
        if x is not None:
            self.fit(x)

    def fit(self, x):
        s = x.shape
        x = x.copy().reshape((s[0],np.prod(s[1:])))
        m = np.mean(x, axis=0)
        x -= m
        sigma = np.dot(x.T,x) / x.shape[0]
        U, S, V = np.linalg.svd(sigma)
        tmp = np.dot(U, np.diag(1./np.sqrt(S+self.regularization)))
        tmp2 = np.dot(U, np.diag(np.sqrt(S+self.regularization)))
        self.ZCA_mat = theano.shared(np.dot(tmp, U.T).astype(theano.config.floatX))
        self.inv_ZCA_mat = theano.shared(np.dot(tmp2, U.T).astype(theano.config.floatX))
        self.mean = theano.shared(m.astype(theano.config.floatX))

    def apply(self, x):
        s = x.shape
        if isinstance(x, np.ndarray):
            return np.dot(x.reshape((s[0],np.prod(s[1:]))) - self.mean.get_value(), self.ZCA_mat.get_value()).reshape(s)
        elif isinstance(x, T.TensorVariable):
            return T.dot(x.flatten(2) - self.mean.dimshuffle('x',0), self.ZCA_mat).reshape(s)
        else:
            raise NotImplementedError("Whitening only implemented for numpy arrays or Theano TensorVariables")
            
    def invert(self, x):
        s = x.shape
        if isinstance(x, np.ndarray):
            return (np.dot(x.reshape((s[0],np.prod(s[1:]))), self.inv_ZCA_mat.get_value()) + self.mean.get_value()).reshape(s)
        elif isinstance(x, T.TensorVariable):
            return (T.dot(x.flatten(2), self.inv_ZCA_mat) + self.mean.dimshuffle('x',0)).reshape(s)
        else:
            raise NotImplementedError("Whitening only implemented for numpy arrays or Theano TensorVariables")