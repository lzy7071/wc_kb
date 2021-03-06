""" Reading and writing knowledge bases to/from files.

Supported file types:

* Comma separated values (.csv)
* Excel (.xlsx)
* Tab separated values (.tsv)

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2018-02-12
:Copyright: 2018, Karr Lab
:License: MIT
"""

from . import core
from . import eukaryote_schema
from . import prokaryote_schema
from . import util
from wc_utils.util.string import indent_forest
import Bio.SeqIO
import Bio.SeqRecord
import obj_model
import os
import shutil
import wc_utils.cache
import wc_kb


PROKARYOTE_MODEL_ORDER = (
    core.KnowledgeBase,
    core.Cell,
    core.Compartment,
    core.MetaboliteSpeciesType,
    core.DnaSpeciesType,
    prokaryote_schema.PromoterLocus,
    prokaryote_schema.TranscriptionUnitLocus,
    prokaryote_schema.RnaSpeciesType,
    prokaryote_schema.GeneLocus,
    prokaryote_schema.ProteinSpeciesType,
    core.ComplexSpeciesType,
    core.Concentration,
    core.Reaction,
    core.RateLaw,
    core.Parameter,
    core.Property,
    core.Observable,
    core.Reference
    )   

EUKARYOTE_MODEL_ORDER = (
    core.KnowledgeBase,
    core.Cell,
    core.Compartment,
    core.MetaboliteSpeciesType,
    core.DnaSpeciesType,
    eukaryote_schema.GeneLocus,
    eukaryote_schema.RegulatoryElementLocus,
    eukaryote_schema.RegulatoryModule,    
    eukaryote_schema.PreRnaSpeciesType,    
    eukaryote_schema.TranscriptSpeciesType,
    eukaryote_schema.ExonLocus,
    eukaryote_schema.ProteinSpeciesType,
    eukaryote_schema.CdsLocus,
    core.ComplexSpeciesType,
    core.Concentration,
    core.Observable,
    core.Reaction,
    core.RateLaw,
    core.Parameter,
    core.Property,    
    core.Reference
    ) 


class Writer(object):
    """ Write knowledge base to file(s) """

    def run(self, knowledge_base, core_path, seq_path=None, rewrite_seq_path=False, schema=True, set_repo_metadata_from_path=True):
        """ Write knowledge base to file(s)

        Args:
            knowledge_base (:obj:`core.KnowledgeBase`): knowledge base
            core_path (:obj:`str`): path to save core knowledge base
            seq_path (:obj:`str`, optional): path to save genome sequence
            rewrite_seq_path (:obj:`bool`, optional): if :obj:`True`, the path to genome sequence in the saved knowledge base
                will be updated to the newly saved seq_path 
            schema (:obj:`bool`, optional): if :obj:`True`, use model order for prokaryote, else use model order for eukaryote
            set_repo_metadata_from_path (:obj:`bool`, optional): if :obj:`True`, set the Git repository metadata (URL,
                branch, revision) for the knowledge base from the parent directory of :obj:`core_path`

        Raises:
            :obj:`ValueError`: if any of the relationships with knowledge bases and cells are not set
        """
        if schema:
            self.model_order = PROKARYOTE_MODEL_ORDER
        else:
            self.model_order = EUKARYOTE_MODEL_ORDER            

        self.validate_implicit_relationships()

        # check that there is only 1 :obj:`KnowledgeBase` and <= 1 :obj:`Cell` and that each relationship
        # to :obj:`KnowledgeBase` and :obj:`Cell` is set. This is necessary to enable the :obj:`KnowledgeBase` and
        # :obj:`Cell` relationships to be implicit in the Excel output and added by :obj:`Reader.run`
        cell = knowledge_base.cell

        for obj in knowledge_base.get_related():
            for attr in obj.Meta.attributes.values():
                if isinstance(attr, obj_model.RelatedAttribute) and attr.related_class == core.Cell:
                    val = getattr(obj, attr.name)
                    if val is None or val != cell:
                        raise ValueError('{}.{} must be set to the instance of `Cell`'.format(
                            obj.__class__.__name__, attr.name))

        # set Git repository metadata from the parent directories of :obj:`core_path`
        if set_repo_metadata_from_path:
            util.set_git_repo_metadata_from_path(knowledge_base, core_path)

        # export sequences if a path is provided
        if seq_path:
            dna_seqs = []
            if cell:
                dna_species_types = cell.species_types.get(
                    __type=core.DnaSpeciesType)
                for species_type in dna_species_types:
                    dna_seqs.append(Bio.SeqRecord.SeqRecord(
                        species_type.get_seq(), species_type.id))
                    if rewrite_seq_path:
                        species_type.sequence_path = seq_path    
            
            with open(seq_path, 'w') as file:
                writer = Bio.SeqIO.FastaIO.FastaWriter(
                    file, wrap=70, record2title=lambda record: record.id)
                writer.write_file(dna_seqs)            

        # export core
        _, ext = os.path.splitext(core_path)
        writer = obj_model.io.get_writer(ext)()

        kwargs = {}
        if isinstance(writer, obj_model.io.WorkbookWriter):
            kwargs['include_all_attributes'] = False

        writer.run(core_path, [knowledge_base], models=self.model_order,
                   language='wc_kb',
                   creator='{}.{}'.format(
                       self.__class__.__module__, self.__class__.__name__),
                   title=knowledge_base.id,
                   description=knowledge_base.name,
                   version=knowledge_base.version,
                   **kwargs)       

    @classmethod
    def validate_implicit_relationships(cls):
        """ Check that relationships to :obj:`core.KnowledgeBase` and :obj:`core.Cell` do not need to be explicitly written to
        workbooks because they can be inferred by :obj:`Reader.run`

        Raises:
            :obj:`Exception`: if the Excel serialization involves an unsupported implicit relationship
        """
        for name, attr in core.KnowledgeBase.Meta.attributes.items():
            if isinstance(attr, obj_model.RelatedAttribute):
                raise Exception(
                    "Relationships from `KnowledgeBase` not supported: {}.{} to {}".format(
                        'KnowledgeBase', name, attr.related_class.__name__))

        for name, attr in core.KnowledgeBase.Meta.related_attributes.items():
            if not isinstance(attr, obj_model.OneToOneAttribute):
                raise Exception(
                    "Relationships to `KnowledgeBase` that are not one-to-one are prohibited: {}.{} to {}".format(
                        attr.related_class.__name__, name, 'KnowledgeBase'))

        for name, attr in core.Cell.Meta.attributes.items():
            if isinstance(attr, obj_model.RelatedAttribute):
                if not isinstance(attr, obj_model.OneToOneAttribute):
                    raise Exception(
                        "Relationships from `Cell` to `KnowledgeBase` that are not one-to-one are prohibited: {}.{} to {}".format(
                            'Cell', name, 'KnowledgeBase'))
                if attr.related_class != core.KnowledgeBase:
                    raise Exception(
                        "Relationships from `Cell` to classes other than `KnowledgeBase` are prohibited: {}.{} to {}".format(
                            'Cell', name, attr.related_class.__name__))

        for attr in core.Cell.Meta.related_attributes.values():
            if not isinstance(attr, (obj_model.OneToOneAttribute, obj_model.ManyToOneAttribute)):
                raise Exception(
                    "Relationships to `Cell` that are not one-to-one or many-to-one are prohibited: {}.{} to {}".format(
                        attr.related_class.__name__, attr.related_name, 'Cell'))

        for name, attr in core.KnowledgeBase.Meta.related_attributes.items():
            if attr.primary_class != core.Cell:
                raise Exception(
                    "Relationships to `KnowledgeBase` from classes other than `Cell` are prohibited: {}.{} to {}".format(
                        attr.related_class.__name__, name, 'KnowledgeBase'))

        return None # pragma: no cover; avoids missing branch coverage on previous for loop

class Reader(object):
    """ Read knowledge base from file(s) """

    #@wc_utils.cache.memoize(filename_args=[1, 2])
    def run(self, core_path, seq_path, rewrite_seq_path=True, schema=True, strict=True):
        """ Read knowledge base from file(s)

        Args:
            core_path (:obj:`str`): path to core knowledge base
            seq_path (:obj:`str`): path to genome sequence
            rewrite_seq_path (:obj:`bool`, optional): if :obj:`True`, the path to genome sequence in the knowledge base
                will be updated to the provided seq_path 
            schema (:obj:`bool`, optional): if :obj:`True`, use model order for prokaryote, else use model order for eukaryote
            strict (:obj:`bool`, optional): if :obj:`True`, validate that the the model file(s) strictly follow the
                :obj:`obj_model` serialization format:

                * The worksheets are in the expected order
                * There are no missing worksheets
                * There are no extra worksheets
                * The columns are in the expected order
                * There are no missing columns
                * There are no extra columns

        Returns:
            :obj:`core.KnowledgeBase`: knowledge base

        Raises:
            :obj:`ValueError`: if :obj:`core_path`

                * Defines multiple knowledge bases or cells
                * Represents objects that cannot be linked to a knowledge base and/or cell
        """
        Writer.validate_implicit_relationships()

        if schema:
            model_order = PROKARYOTE_MODEL_ORDER
        else:
            model_order = EUKARYOTE_MODEL_ORDER      

        # read core objects from file
        _, ext = os.path.splitext(core_path)
        reader = obj_model.io.get_reader(ext)()

        kwargs = {}
        if isinstance(reader, obj_model.io.WorkbookReader):
            kwargs['include_all_attributes'] = False
            if not strict:
                kwargs['ignore_missing_sheets'] = True
                kwargs['ignore_extra_sheets'] = True
                kwargs['ignore_sheet_order'] = True
                kwargs['ignore_missing_attributes'] = True
                kwargs['ignore_extra_attributes'] = True
                kwargs['ignore_attribute_order'] = True          

        objects = reader.run(
            core_path, models=model_order, validate=False, **kwargs)

        # check that file has 0 or 1 knowledge bases
        if not objects[core.KnowledgeBase]:
            for model, model_objects in objects.items():
                if model_objects:
                    raise ValueError('"{}" cannot contain instances of `{}` without an instance of `KnowledgeBase`'.format(
                        core_path, model.__name__))
            return None

        elif len(objects[core.KnowledgeBase]) > 1:
            raise ValueError(
                '"{}" should define one knowledge base'.format(core_path))

        else:
            kb = objects[core.KnowledgeBase].pop()

        # check that file has 0 or 1 cells
        if not objects[core.Cell]:
            for model, model_objects in objects.items():
                if model_objects:
                    raise ValueError('"{}" cannot contain instances of `{}` without an instance of `Cell`'.format(
                        core_path, model.__name__))
            cell = None

        elif len(objects[core.Cell]) > 1:
            raise ValueError('"{}" should define one cell'.format(core_path))

        else:
            cell = objects[core.Cell].pop()

        # add implict relationships to `KnowledgeBase` and `Cell`
        kb.cell = cell

        for model, model_objects in objects.items():
            for attr in model.Meta.attributes.values():
                if isinstance(attr, obj_model.RelatedAttribute) and attr.related_class == core.Cell:
                    for model_obj in model_objects:
                        setattr(model_obj, attr.name, cell)

        # link path to genome sequence to the DNA species types if rewrite_seq_path is True
        if rewrite_seq_path:
            for dna in Bio.SeqIO.parse(seq_path, "fasta"):
                kb.cell.species_types.get_one(id=dna.id).sequence_path = seq_path

        # validate
        objs = []
        for cls_objs in objects.values():
            objs.extend(cls_objs)

        errors = obj_model.Validator().validate(objs)
        if errors:
            raise ValueError(
                indent_forest(['The knowledge base cannot be loaded because it fails to validate:', [errors]]))

        # return kb
        return kb


def convert(source_core, source_seq, dest_core, dest_seq, rewrite_seq_path=False, strict=True):
    """ Convert among Excel (.xlsx), comma separated (.csv), and tab separated (.tsv) file formats

    Read a knowledge base from the `source` files(s) and write it to the `destination` files(s). A path to a
    delimiter separated set of knowledge base files must be represented by a Unix glob pattern (with a \\*) that
    matches all delimiter separated files.

    Args:
        source_core (:obj:`str`): path to the core of the source knowledge base
        source_seq (:obj:`str`): path to the genome sequence of the source knowledge base
        dest_core (:obj:`str`): path to save the converted core of the knowledge base
        dest_seq (:obj:`str`): path to save the converted genome sequence of the knowledge base
        rewrite_seq_path (:obj:`bool`, optional): if :obj:`True`, the path to genome sequence in the converted
            core of the knowledge base will be updated to the path of the converted genome sequence 
        strict (:obj:`bool`, optional): if :obj:`True`, validate that the the model file(s) strictly follow the
                :obj:`obj_model` serialization format:

                * The worksheets are in the expected order
                * There are no missing worksheets
                * There are no extra worksheets
                * The columns are in the expected order
                * There are no missing columns
                * There are no extra columns
    """
    kb = Reader().run(source_core, source_seq, strict=strict)
    Writer().run(kb, dest_core, dest_seq, rewrite_seq_path=rewrite_seq_path, set_repo_metadata_from_path=False)


def create_template(core_path, seq_path, set_repo_metadata_from_path=True):
    """ Create file with knowledge base template, including row and column headings

    Args:
        core_path (:obj:`str`): path to save template of core knowledge base
        seq_path (:obj:`str`): path to save genome sequence
        set_repo_metadata_from_path (:obj:`bool`, optional): if :obj:`True`, set the Git repository metadata (URL,
            branch, revision) for the knowledge base from the parent directory of :obj:`core_path`
    """
    kb = core.KnowledgeBase(
        id='template', name='Template', version=wc_kb.__version__)
    Writer().run(kb, core_path, seq_path,
                 set_repo_metadata_from_path=set_repo_metadata_from_path)
