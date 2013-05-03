"""Example showing how to compute a covariance matrix between brain regions.

**Running this script may require to set the dirname parameter in the
load_harvard_oxford() function below**.

The following things are performed:
- improvement of fMRI data SNR (confound removal, filtering, etc.)
- parcellation loading, and signals extraction
- covariance/precision matrices computation
- display of matrices

This script is intended for advanced users only, since it makes use of
low-level functions.
"""
import numpy as np
import pylab as pl
import matplotlib

from sklearn import covariance

import nibabel

import nisl.signals
import nisl.masking
import nisl.region
import nisl.datasets as datasets


# Copied from matplotlib 1.2.0 for matplotlib 0.99
_bwr_data = ((0.0, 0.0, 1.0), (1.0, 1.0, 1.0), (1.0, 0.0, 0.0))
pl.cm.register_cmap(cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
    "bwr", _bwr_data))


def plot_matrices(cov, prec, title, subject_n=0):
    """Plot covariance and precision matrices, for a given processing. """

    # Put zeros on the diagonal, for graph clarity.
    size = prec.shape[0]
    prec[range(size), range(size)] = 0

    span = max(abs(prec.min()), abs(prec.max()))
    title = "{0:d} {1}".format(subject_n, title)

    # Display covariance matrix
    pl.figure()
    pl.imshow(cov, interpolation="nearest",
              vmin=-1, vmax=1, cmap=pl.cm.get_cmap("bwr"))
    pl.hlines([(pl.ylim()[0] + pl.ylim()[1]) / 2],
              pl.xlim()[0], pl.xlim()[1])
    pl.vlines([(pl.xlim()[0] + pl.xlim()[1]) / 2],
              pl.ylim()[0], pl.ylim()[1])
    pl.colorbar()
    pl.title(title + " / covariance")

    # Display precision matrix
    pl.figure()
    pl.imshow(prec, interpolation="nearest",
              vmin=-span, vmax=span,
              cmap=pl.cm.get_cmap("bwr"))
    pl.hlines([(pl.ylim()[0] + pl.ylim()[1]) / 2],
              pl.xlim()[0], pl.xlim()[1])
    pl.vlines([(pl.xlim()[0] + pl.xlim()[1]) / 2],
              pl.ylim()[0], pl.ylim()[1])
    pl.colorbar()
    pl.title(title + " / precision")


if __name__ == "__main__":
    subject_n = 1

    dataset = datasets.fetch_adhd()
    filename = dataset["func"][subject_n]
    confound_file = dataset["confounds"][subject_n]

    print("-- Loading raw data ({0:d}) and masking ...".format(subject_n))
    regions_img = datasets.load_harvard_oxford(
        "cort-maxprob-thr25-2mm", symmetric_split=True)
    mask_img = nisl.region.regions_to_mask(regions_img)

    print("-- Computing confounds ...")
    # On full image
    fmri_img = nibabel.load(filename)
    fmri_masked = fmri_img.get_data(
        )[np.ones(fmri_img.shape[:3], dtype=np.bool)].T
    hv_confounds = nisl.signals.high_variance_confounds(fmri_masked)
    mvt_confounds = np.loadtxt(confound_file, skiprows=1)
    confounds = np.hstack((hv_confounds, mvt_confounds))

    print("-- Cleaning signals ...")
    # On regions only
    fmri_masked = nisl.masking.apply_mask(fmri_img, mask_img)
    timeseries = nisl.signals.clean(fmri_masked, low_pass=None,
                                    detrend=True, standardize=True,
                                    confounds=confounds,
                                    t_r=2.5, high_pass=0.01
                                    )
    fmri_img = nisl.masking.unmask(timeseries, mask_img)

    print("-- Computing region signals ...")
    region_ts, _ = nisl.region.signals_from_labels(fmri_img, regions_img)
    region_ts /= region_ts.std(axis=0)

    print("-- Computing covariance matrices ...")
    estimator = covariance.GraphLassoCV()
    estimator.fit(region_ts)

    plot_matrices(estimator.covariance_, -estimator.precision_,
                  title="Graph Lasso CV ({0:.3f})".format(estimator.alpha_),
                  subject_n=subject_n)
    pl.show()
