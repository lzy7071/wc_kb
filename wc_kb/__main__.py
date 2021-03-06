""" Command line programs for managing knowledge bases for whole-cell models

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2018-04-20
:Copyright: 2018, Karr Lab
:License: MIT
"""

from wc_kb import io
import cement
import wc_kb
import wc_utils.workbook.io


class BaseController(cement.Controller):
    """ Base controller for command line application """

    class Meta:
        label = 'base'
        description = "Command line programs for managing knowledge bases for whole-cell models"
        arguments = [
            (['-v', '--version'], dict(action='version', version=wc_kb.__version__)),
        ]

    @cement.ex(hide=True)
    def _default(self):
        self._parser.print_help()


class ValidateController(cement.Controller):
    """ Validate knowledge base and display errors """

    class Meta:
        label = 'validate'
        description = 'Validate knowledge base and display errors'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
            (['core_path'], dict(type=str, help='Path to knowledge base core')),
            (['seq_path'], dict(type=str, help='Path to FASTA-formatted genome sequence')),
            (['--sloppy'], dict(dest='strict', default=True, action='store_false',
                                help='If set, do not validate the format of the knowledge base core file(s)')),
        ]

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs
        try:
            io.Reader().run(args.core_path, args.seq_path, strict=args.strict)
            print('Knowledge base is valid')
        except ValueError as exception:
            raise SystemExit('Knowledge base is invalid: ' + str(exception))


class DifferenceController(cement.Controller):
    """ Display difference between two knowledge bases """

    class Meta:
        label = 'difference'
        description = 'Get difference between two knowledge bases'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
            (['core_path_1'], dict(type=str, help='Path to core for first knowledge base')),
            (['seq_path_1'], dict(type=str, help='Path to FASTA-formatted genome sequence for first knowledge base')),
            (['core_path_2'], dict(type=str, help='Path to core for second knowledge base')),
            (['seq_path_2'], dict(type=str, help='Path to FASTA-formatted genome sequence for second knowledge base')),
            (['--compare-files'], dict(dest='compare_files', default=False, action='store_true',
                                       help='If true, compare knowledge bases; otherwise compare files directly')),
            (['--sloppy'], dict(dest='strict', default=True, action='store_false',
                                help='If set, do not validate the format of the knowledge base file(s)')),
        ]

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs

        if args.compare_files:
            kb1 = wc_utils.workbook.io.read(args.core_path_1)
            kb2 = wc_utils.workbook.io.read(args.core_path_2)
            diff = kb1.difference(kb2)

        else:
            kb1 = io.Reader().run(args.core_path_1, args.seq_path_1, strict=args.strict)
            kb2 = io.Reader().run(args.core_path_2, args.seq_path_2, strict=args.strict)
            diff = kb1.difference(kb2)

        if diff:
            print(diff)
        else:
            print('Knowledge bases are identical')


class NormalizeController(cement.Controller):
    """ Normalize knowledge base """

    class Meta:
        label = 'normalize'
        description = 'Normalize knowledge base'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
            (['source_core'], dict(
                type=str,
                help='Path to core of the knowledge base')),
            (['source_seq'], dict(
                type=str,
                help='Path to FASTA-formatted genome sequence for the knowledge base')),
            (['--dest-core'], dict(
                default='', type=str,
                help='Path to save normalized core of the knowledge base')),
            (['--dest-seq'], dict(
                default='', type=str,
                help='Path to save normalized FASTA-formatted genome sequence for the knowledge base')),
            (['--sloppy'], dict(
                dest='strict', default=True, action='store_false',
                help='If set, do not validate the format of the knowledge base file(s)')),
        ]

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs
        kb = io.Reader().run(args.source_core, args.source_seq, strict=args.strict)
        if args.dest_core or args.dest_seq:
            io.Writer().run(kb, args.dest_core, args.dest_seq, set_repo_metadata_from_path=False)
        else:
            io.Writer().run(kb, args.source_core, args.source_seq, set_repo_metadata_from_path=False)


class ConvertController(cement.Controller):
    """ Convert knowledge base among Excel (.xlsx), comma separated (.csv), JavaScript Object Notation (.json),
    tab separated (.tsv), and Yet Another Markup Language (.yaml, .yml) formats """

    class Meta:
        label = 'convert'
        description = 'Convert knowledge base among .csv, .json, .tsv, .xlsx, .yaml, and .yml formats'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
            (['source_core'], dict(type=str, help='Path to core of the knowledge base')),
            (['source_seq'], dict(type=str, help='Path to FASTA-formatted genome sqeuence of the knowledge base')),
            (['dest_core'], dict(type=str, help='Path to save the converted core of the knowledge base')),
            (['dest_seq'], dict(type=str, help='Path to save the converted FASTA-formatted genome sequence of the knowledge base')),
            (['--sloppy'], dict(dest='strict', default=True, action='store_false',
                                help='If set, do not validate the format of the knowledge base file(s)')),
        ]

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs
        io.convert(args.source_core, args.source_seq, args.dest_core, args.dest_seq, strict=args.strict)


class CreateTemplateController(cement.Controller):
    """ Create file with knowledge base template (i.e. create file with row and column labels) """

    class Meta:
        label = 'create-template'
        description = 'Create file with knowledge base template: blank file(s) with row and column labels'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
            (['path_core'], dict(metavar='path-core', type=str, help='Path to save a template of the core of a knowledge base')),
            (['path_seq'], dict(metavar='path-seq', type=str, help='Path to save a template of the genome sequence of a knowledge base')),
            (['--ignore-repo-metadata'], dict(dest='set_repo_metadata_from_path', default=True, action='store_false',
                                              help=('If set, do not set the Git repository metadata for the knowledge base from '
                                                    'the parent directory of `path-core`'))),
        ]

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs
        io.create_template(args.path_core, args.path_seq, set_repo_metadata_from_path=args.set_repo_metadata_from_path)


class UpdateVersionMetadataController(cement.Controller):
    """ Update version metadata of a knowledge base (URL, branch, revision, wc_kb version) """

    class Meta:
        label = 'update-version-metadata'
        description = 'Update version metadata of a knowledge base (URL, branch, revision, wc_kb version)'
        stacked_on = 'base'
        stacked_type = 'nested'
        arguments = [
            (['path_core'], dict(type=str, help='Path to the core of the knowledge base')),
            (['path_seq'], dict(type=str, help='Path to the FASTA-formatted genome sequence of a knowledge base')),
            (['--ignore-repo-metadata'], dict(dest='set_repo_metadata_from_path', default=True, action='store_false',
                                              help=('If set, do not set the Git repository metadata for the knowledge base from '
                                                    'the parent directory of `path-core`'))),
            (['--sloppy'], dict(dest='strict', default=True, action='store_false',
                                help='If set, do not validate the format of the knowledge base file(s)')),
        ]

    @cement.ex(hide=True)
    def _default(self):
        args = self.app.pargs
        kb = io.Reader().run(args.path_core, args.path_seq, strict=args.strict)
        kb.wc_kb_version = wc_kb.__version__
        io.Writer().run(kb, args.path_core, args.path_seq, set_repo_metadata_from_path=args.set_repo_metadata_from_path)


class App(cement.App):
    """ Command line application """
    class Meta:
        label = 'wc_kb'
        base_controller = 'base'
        handlers = [
            BaseController,
            ValidateController,
            DifferenceController,
            NormalizeController,
            ConvertController,
            CreateTemplateController,
            UpdateVersionMetadataController,
        ]


def main():
    with App() as app:
        app.run()
