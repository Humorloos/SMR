from .statusmanager import StatusManager
from .xmanager import *
from .xnotemanager import *
from .xontology import XOntology, get_rel_dict
from .xmindimport import XmindImporter


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
        self.translator = FieldTranslator()

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

    def add_remote_a(self, importer, meta, note, q_content, q_id, remote,
                     status, a_tag):
        a_content = self.map_manager.getNodeContent(a_tag)
        a_field = field_from_content(a_content)

        # Add answer to note fields
        a_index = get_topic_index(a_tag)
        if not note:
            note = self.note_manager.get_note_from_q_id(q_id)
        note.fields[get_index_by_field_name('a' + str(a_index))] = a_field
        a_media = a_content['media']
        if a_media['image'] or a_media['media']:
            if not importer:
                importer = XmindImporter(col=self.note_manager.col,
                                         file=self.map_manager.file)
            if a_media['image']:
                importer.images.append(a_media['image'])
            if a_media['media']:
                importer.media.append(a_media['media'])

        # Add answer to ontology
        if not q_content:
            q_content = content_from_field(field_by_name(note.fields, 'qt'))
        if not meta:
            meta = meta_from_fields(note.fields)
        q_class = self.translator.classify(q_content)
        rel_dict = get_rel_dict(
            aIndex=a_index,
            image=q_content['media']['image'],
            media=q_content['media']['media'],
            x_id=q_id,
            ref=field_by_name(note.fields, 'rf'),
            sortId=field_by_name(note.fields, 'id'),
            doc=self.map_manager.file,
            sheet=meta['sheetId'],
            tag=note.tags[0]
        )
        a_concept = self.onto.add_answer(
            a_id=a_tag['id'], answer_field=a_field, rel_dict=rel_dict,
            question_class=q_class)
        # Add answer to status
        # a_cards = self.note_manager.get_answer_cards(note.id)
        # local_a_dict = local_answer_dict(anki_mod = a_card[])
        status['answers'][a_tag['id']] = remote['answers'][a_tag['id']]
        return importer, note, meta

    def add_remote_as(self, note, q_content, q_id, remote, status, importer):
        meta = None
        not_in_status = [a for a in remote['answers'] if a not in status[
            'answers']]
        for a_id in not_in_status:
            a_tag = self.map_manager.getTagById(a_id)
            importer, note, meta = self.add_remote_a(
                importer=importer, meta=meta, note=note, q_content=q_content,
                q_id=q_id, remote=remote, status=status, a_tag=a_tag)
        return note, importer

    def change_answer(self, answer, question, local, status):

        # Change answer in map
        title = title_from_field(local[answer]['content'])
        img = img_from_field(local[answer]['content'])
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
                       {question: {answer: change_dict(
                           old=status[answer]['content'],
                           new=local[answer]['content'])}}))

        # Change answer in status
        status[answer].update(local[answer])

    def process_note(self, q_id, status, remote, deck_id, sheet_id):
        note = None
        q_content = None
        ref_changes = {}
        sort_id_changes = {}
        importer = None
        if not status['xMod'] == remote['xMod']:
            note = self.note_manager.get_note_from_q_id(q_id)
            q_content = self.map_manager.content_by_id(q_id)
            new_q_field = field_from_content(q_content)
            q_index = get_index_by_field_name('qt')

            # Add change to changes dict
            ref_changes['question'] = change_dict(
                old=note.fields[q_index], new=new_q_field)

            # Change question field to new question
            note.fields[q_index] = new_q_field

            # Change question in ontology
            self.onto.change_question(x_id=q_id, new_question=new_q_field)

            # Adjust question in status
            status['xMod'] = remote['xMod']

        # Adjust index if it has changed
        if not status['index'] == remote['index']:
            q_topic = self.map_manager.getTagById(q_id)
            level = len(self.map_manager.ref_and_sort_id(q_topic)[1])
            new_sort_id = sort_id_from_index(remote['index'])

            # Add change to changes dict
            sort_id_changes['question'] = change_dict(
                old=level, new=new_sort_id)

            # Adjust index in status
            status['index'] = remote['index']

        # Add new answers if there are any
        note, importer = self.add_remote_as(
            note=note, q_content=q_content, q_id=q_id, remote=remote,
            status=status, importer=importer)

        # Remove old answers if there are any
        note = self.remove_remote_as(
            status=status['answers'], remote=remote['answers'], note=note,
            q_id=q_id)

    def change_remote_question(self, question, status, local):
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
            'question': change_dict(
                old=status[question]['content'],
                new=local[question]['content'])}

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
        self.note_manager.set_meta(note=question_note, meta=meta)

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
                if f not in status:
                    importer = XmindImporter(col=self.note_manager.col, file=f)
                    importer.init_import(deck_id=d, repair=False)
                    continue
                local_change = status[f]['ankiMod'] != local[f]['ankiMod']
                if status[f]['osMod'] != os_file_mods[f]:
                    self.map_manager = XManager(f)
                    for file in self.map_manager.get_ref_files():
                        if file not in self.xmind_files:
                            self.xmind_files.append(file)
                    remote_file = self.map_manager.remote_file()
                    remote_change = status[f]['xMod'] != remote_file['xMod']
                    status[f]['osMod'] = os_file_mods[f]
                else:
                    remote_change = False
                if not local_change and not remote_change:
                    continue
                elif local_change and not remote_change:
                    if not self.onto:
                        self.onto = XOntology(d)
                    self.map_manager = XManager(f)
                    self.process_local_changes(status=status[f]['sheets'],
                                               local=local[f]['sheets'])

                    # Adjust notes according to self.change_list
                    self.process_change_list()
                    self.map_manager.save_changes()
                elif not local_change and remote_change:
                    remote_sheets = self.map_manager.get_remote_sheets()
                    # noinspection PyUnboundLocalVariable
                    self.process_remote_changes(status=status[f]['sheets'],
                                                remote=remote_sheets, deck_id=d)
                else:
                    print('')
            if self.onto:
                self.onto.save_changes()
        self.note_manager.save_col()

    def process_change_list(self):
        for sheet in self.change_list:
            changed_notes = [self.note_manager.get_note_from_q_id(q_id) for
                             q_id in self.change_list[sheet]]
            for note in changed_notes:
                meta = meta_from_fields(note.fields)
                changes = self.change_list[sheet][meta['questionId']]
                self.note_manager.update_ref(note=note, changes=changes,
                                             meta=meta)

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
                self.change_remote_question(question, status, local)
            self.process_local_answers(status=status[question]['answers'],
                                       local=local[question]['answers'],
                                       question=question)
            print()

    def process_remote_changes(self, status, remote, deck_id):
        for sheet in {**remote, **status}:
            if sheet not in status:
                importer = XmindImporter(self.note_manager.col,
                                         self.map_manager.file)
                importer.importMap(sheet=sheet, deck_id=deck_id)
                importer.finish_import()
            elif sheet not in remote:
                if not self.onto:
                    self.onto = XOntology(deck_id)
                self.remove_sheet(sheet, status)
            elif remote[sheet]['xMod'] != status[sheet]['xMod']:
                if not self.onto:
                    self.onto = XOntology(deck_id)
                print('process_remote_questions')
                remote_questions = self.map_manager.get_remote_questions(sheet)
                self.process_remote_questions(
                    status=status[sheet]['questions'], remote=remote_questions,
                    deck_id=deck_id, sheet_id=sheet)

    def process_remote_questions(self, status, remote, deck_id, sheet_id):
        note = None

        # Remove questions that were removed in map
        not_in_remote = [q for q in status if q not in remote]
        self.remove_questions(q_ids=not_in_remote, status=status)

        # Add questions that were added in map
        not_in_status = [q for q in remote if q not in status]
        tags_to_add = [self.map_manager.getTagById(q) for q in not_in_status]
        if tags_to_add:
            tags_and_parent_qs = [{'tag': t,
                                   'parent_q': get_parent_question_topic(t)} for
                                  t in tags_to_add]

            # Get all questions whose parent question is already in status,
            # since they are the starting points for the imports
            seed_dicts = [d for d in tags_and_parent_qs if
                          d['parent_q']['id'] in status]
            importer = XmindImporter(col=self.note_manager.col,
                                     file=self.map_manager.file,
                                     status_manager=self.status_manager)
            for seed_dict in seed_dicts:
                parent_as = get_parent_a_topics(
                    q_topic=seed_dict['tag'], parent_q=seed_dict['parent_q'])

                # If the parent answer of this new question is not yet in
                # status, add the answer before importing from the question
                for a in parent_as:
                    if a['id'] not in \
                            status[seed_dict['parent_q']['id']]['answers']:
                        if not note:
                            note = self.note_manager.get_note_from_q_id(
                                seed_dict['parent_q']['id'])
                        q_content = self.map_manager.getNodeContent(
                            seed_dict['parent_q'])
                        meta = meta_from_fields(note.fields)
                        self.add_remote_a(
                            importer=importer, meta=meta, note=note,
                            q_content=q_content,
                            q_id=seed_dict['parent_q']['id'],
                            remote=remote[seed_dict['parent_q']['id']],
                            status=status[seed_dict['parent_q']['id']],
                            a_tag=a)
                        self.note_manager.save_note(note)
                importer.partial_import(
                    seed_topic=seed_dict['tag'], sheet_id=sheet_id,
                    deck_id=deck_id, parent_q=seed_dict['parent_q'],
                    parent_as=parent_as, onto=self.onto)
            importer.finish_import()

            # Add questions to status
            importer_status = next(
                f for f in importer.statusManager.status if
                f['file'] == self.map_manager.file)['sheets'][sheet_id][
                'questions']
            status = importer_status

        for question in {**status, **remote}:
            self.process_note(q_id=question, status=status[question],
                              remote=remote[question])
        print()

    def remove_questions(self, q_ids, status):
        self.note_manager.remove_notes_by_q_ids(q_ids)
        self.onto.remove_questions(q_ids)
        for q_id in q_ids:
            del status[q_id]

    def remove_remote_as(self, status, remote, note, q_id):
        not_in_remote = [a for a in status if a not in remote]
        for a_id in not_in_remote:

            # Remove answer from note fields
            if not note:
                note = self.note_manager.get_note_from_q_id(q_id)
            note.fields[get_index_by_field_name(
                'a' + str(status[a_id]['index']))] = ''

            # Remove answer from ontology
            self.onto.remove_answer(q_id=q_id, a_id=a_id)

            # Remove answer from status
            del status[a_id]
        return note

    def remove_sheet(self, sheet, status):
        self.note_manager.remove_sheet(sheet)
        del status[sheet]
        self.onto.remove_sheet(sheet)
