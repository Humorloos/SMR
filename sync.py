from .consts import USER_PATH
from .statusmanager import StatusManager
from .xmanager import XManager, get_os_mod
from .xnotemanager import *
from .xontology import XOntology


def raise_sync_error(content, question_note, text_pre, text_post):
    tag = question_note.tags[0]
    question_title = field_by_name(
        question_note.fields, 'qt')
    reference = field_by_name(
        question_note.fields, 'rf')
    raise ReferenceError(
        text_pre + content + '" to question "' + question_title +
        '" in map "' + tag + '" (reference "' + reference + '"). ' +
        text_post)


# Algorithm for synchronization was adopted from
# https://unterwaditzer.net/2016/sync-algorithm.html
class XSyncer:
    def __init__(self, col, status_file=None):
        self.col = col
        self.note_manager = XNoteManager(col=col)
        self.xmind_files = self.note_manager.get_xmind_files()
        self.map_manager = None
        self.onto = None
        self.status_manager = StatusManager(status_file=status_file)
        self.change_list = None
        self.current_sheet_sync = None
        self.warnings = []

    # TODO: implement add_answer()
    def add_answer(self, a_id, q_id, local):
        print('add answer to map')
        print('add answer to ontology')
        print('add answer to meta')
        print('add answer to status')
        question_note = self.note_manager.get_note_from_q_id(q_id)
        raise_sync_error(
            content=local[a_id]['content'], question_note=question_note,
            text_pre='Detected added answer "',
            text_post='Adding answers in anki is not supported yet. You can '
                      'add answers directly in the xmind file. Remove the '
                      'answer and try synchronizing again.')

    def change_answer(self, answer, question, local, status):
        # Change answer in map
        # TODO: In case of crosslinks, do not edit the source but delete the
        #  crosslink and add the text directly to the note, don't forget to
        #  remove the crosslink from the ontology afterwards
        title = title_from_field(local[answer]['content'])
        img = img_from_field(local[answer]['content'])
        if status[answer]['crosslink']:
            x_id = status[answer]['crosslink']['x_id']
        else:
            x_id = answer
        self.map_manager.set_node_content(
            img=img, title=title, x_id=x_id,
            media_dir=self.note_manager.media_dir)

        # Change answer in Ontology
        self.onto.change_answer(q_id=question, a_id=answer,
                                new_answer=local[answer]['content'])

        # Remember this change for final note adjustments
        self.change_list[self.current_sheet_sync].update(
            deep_merge(self.change_list[self.current_sheet_sync],
                       {question: {answer: {
                           'old': status[answer]['content'],
                           'new': local[answer]['content']}}}))

        # Change answer in status
        status[answer].update(local[answer])

    def change_question(self, question, status, local):
        # Change question in map
        title = title_from_field(local[question]['content'])
        img = img_from_field(local[question]['content'])
        self.map_manager.set_node_content(
            img=img, title=title, x_id=question,
            media_dir=self.note_manager.media_dir
        )

        # Change question in ontology
        self.onto.change_question(x_id=question,
                                  new_question=local[question]['content'])

        # Remember this change for final note adjustments
        self.change_list[self.current_sheet_sync][question] = {
            'question': {
                'old': status[question]['content'],
                'new': local[question]['content']}}

        # Change question in status
        status[question]['ankiMod'] = local[question]['ankiMod']
        status[question]['content'] = local[question]['content']

    def maybe_remove_answer(self, answer, question, status):
        question_note = self.note_manager.get_note_from_q_id(question)

        # Remove answer from map
        try:
            self.map_manager.remove_node(a_id=answer)
        except AttributeError:
            raise_sync_error(
                content=status[answer]['content'], question_note=question_note,
                text_pre='Detected invalid deletion: Cannot delete answer "',
                text_post='Please restore the answer and try synchronizing '
                          'again. You can delete this answer in the xmind file '
                          'directly.')

        # Remove answer from ontology
        self.onto.remove_answer(question, answer)

        # Remove answer from note meta
        meta = meta_from_fields(question_note.fields)
        meta['answers'].remove(
            next(a for a in meta['answers'] if a['answerId'] == answer))
        meta['nAnswers'] -= 1
        set_meta(note=question_note, meta=meta)

        # Remove answer from status
        del status[answer]

    def run(self):
        local = {f: self.note_manager.get_local(f) for f in self.xmind_files}
        os_file_mods = {f: get_os_mod(f) for f in self.xmind_files}
        status = {d['file']: d for d in self.status_manager.status}
        x_decks = set(local[x_id]['deck'] for x_id in local)
        for d in x_decks:
            self.onto = None
            for f in self.xmind_files:
                self.change_list = {}
                local_change = status[f]['ankiMod'] != local[f]['ankiMod']
                if status[f]['osMod'] != os_file_mods[f]:
                    self.map_manager = XManager(f)
                    remote = self.map_manager.get_remote()
                    remote_change = status[f]['xMod'] != remote['xMod']
                    status[f]['osMod'] = os_file_mods[f]
                else:
                    remote_change = False
                if not local_change and not remote_change:
                    pass
                elif local_change and not remote_change:
                    if not self.onto:
                        self.onto = XOntology(os.path.join(USER_PATH,
                                                           str(d) + '.rdf'))
                    self.map_manager = XManager(f)
                    self.process_local_changes(status=status[f]['sheets'],
                                               local=local[f]['sheets'])

                    # Adjust notes according to self.change_list
                    self.process_change_list()
                    self.map_manager.save_changes()
                    # TODO: save col
                elif not local_change and remote_change:
                    print('')
                else:
                    print('')

    def process_change_list(self):
        for sheet in self.change_list:
            changed_notes = [self.note_manager.get_note_from_q_id(q_id) for
                             q_id in self.change_list[sheet]]
            self.initiate_ref_changes(changed_notes, self.change_list[sheet])
        pass

    def initiate_ref_changes(self, changed_notes, change_list):
        if changed_notes:
            shortest_id_length = min(len(field_by_name(n.fields, 'id'))
                                     for n in changed_notes)
            seed = next(n for n in changed_notes if len(
                field_by_name(n.fields, 'id')) == shortest_id_length)
            sheet_child_notes = self.note_manager.get_sheet_child_notes(seed)
            # TODO: Differentiate child_notes by answer since ref depends on
            #  the answer, best start is by adjusting the uml diagram in the
            #  same manner.
            if sheet_child_notes:
                update_dict = {}
                changes = change_list[
                    meta_from_fields(seed.fields)['questionId']]
                if 'question' in changes.keys():
                    update_dict[changes['question']['old']] = changes[
                        'question']['new']
                # old_ref = field_by_name(
                #     sheet_child_notes[list(
                #         sheet_child_notes.keys())[0]][0].fields, 'rf')
                # for s_id in sheet_child_notes:
                #     answer_field = field_by_name(seed.fields,
                #                                  'a' + index_from_sort_id(s_id))
                #     answer_ref = ref_plus_answer()
                #     print()
                # new_ref = ref_plus_answer(field=new_ref, get_field_by_name(
                #     seed.fields,
                #                                                      'rf'), )
                # for note in sheet_child_notes:

            if sheet_child_notes:
                print()
        pass

    # def adjust_ref(self, note, new_ref=None):
    #     if not new_ref:
    #         new_ref = self.update_ref(note)
    #     pass

    def process_local_answers(self, status, local, question):
        for answer in {**local, **status}:

            # If the answer was removed it is still contained in local
            # (since the id was not removed) but has an empty string as content
            if not local[answer]['content']:
                self.maybe_remove_answer(answer, question, status)

            elif answer not in status:
                self.add_answer(a_id=answer, q_id=question, local=local)
                continue
            elif not status[answer]['content'] == local[answer]['content']:
                self.change_answer(answer=answer, question=question,
                                   local=local, status=status)
            else:
                continue

    def process_local_changes(self, status, local):
        for sheet in {**local, **status}:
            if local[sheet]['ankiMod'] != status[sheet]['ankiMod']:
                self.current_sheet_sync = sheet
                self.change_list[sheet] = {}
                self.process_local_questions(status=status[sheet]['questions'],
                                             local=local[sheet]['questions'])

    def process_local_questions(self, status, local):
        for question in {**local, **status}:
            if local[question]['content'] != status[question]['content']:
                self.change_question(question, status, local)
            self.process_local_answers(status=status[question]['answers'],
                                       local=local[question]['answers'],
                                       question=question)
            print()
    #
    # def update_ref(self, note):
    #     old_ref = get_field_by_name(note.fields, 'rf')
    #
    #     pass
