"""
Class and methods to perform routine sex check on all processed libraries.
"""
import logging

logger = logging.getLogger(__name__)


class SexPredictor(object):
    """
    Predicts sex based X and Y gene count data using a pre-defined rule.
    """
    def __init__(self, data):
        logger.debug("creating `SexPredictor` instance")
        self.data = data

    def _compute_y_x_gene_ratio(self):
        """
        Calculate the ratio of Y genes detected to X genes detected,
        where detected = count > 0.
        """
        n_y = float(self.data['y_genes'])
        n_x = float(self.data['x_genes'])
        if n_x == 0:
            # for now, set ot number of y counts.
            # might be better to set to something very large,
            # or to cutoff + n_y? This nicely handles instance where
            # n_y = n_x = 0
            self.data['y_x_gene_ratio'] = n_y
        else:
            self.data['y_x_gene_ratio'] = (float(self.data['y_genes'])
                                       / float(self.data['x_genes']))

    def _compute_y_x_count_ratio(self):
        """
        Calculate the ratio of Y counts to X counts.
        """
        n_y = float(self.data['y_counts'])
        n_x = float(self.data['x_counts'])
        if n_x == 0:
            self.data['y_x_count_ratio'] = n_y
        else:
            self.data['y_x_count_ratio'] = (float(self.data['y_counts'])
                                       / float(self.data['x_counts']))

    def _predict_sex(self, cutoff=1, equation='y_sq_over_tot'):
        """
        Return predicted sex based on X/Y gene equation and cutoff.
        """
        self._compute_y_x_gene_ratio()
        logger.debug("ratio of detected Y genes to detected X genes: {}"
                     .format(self.data['y_x_gene_ratio']))

        self._compute_y_x_count_ratio()
        logger.debug("ratio of Y counts to X counts: {}"
                     .format(self.data['y_x_count_ratio']))

        possible_eqs={
            'y_sq_over_tot': '(y_counts^2 / total_counts) > cutoff',
            'gene_ratio': '(y_genes / x_genes) > cutoff',
            'count_ratio': '(y_counts / x_counts) > cutoff'
        }
        equation = possible_eqs[equation]
        logger.debug("using equation: {}".format(equation))
        value = (float(self.data['y_counts']**2)
                 / float(self.data['total_counts']))
        logger.debug("value for current sample is {}"
                     .format(value))
        self.data['sexcheck_eqn'] = equation
        self.data['sexcheck_cutoff'] = cutoff

        if value > cutoff:
            self.data['predicted_sex'] = 'male'
        else:
            self.data['predicted_sex'] = 'female'

    def predict(self):
        self._predict_sex()
        return self.data
