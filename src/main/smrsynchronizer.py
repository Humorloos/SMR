from anki import Collection
from aqt import mw
from main.utils import deep_merge
from main.xmanager import get_topic_index, XManager, get_parent_question_topic, get_parent_a_topics
from main.xmindimport import XmindImporter
from main.xnotemanager import field_by_name, XNoteManager, FieldTranslator, field_from_content, meta_from_fields, \
    content_from_field, title_from_field, image_from_field, change_dict, get_index_by_a_id, get_index_by_field_name, \
    sort_id_from_order_number
from main.xontology import XOntology


def raise_sync_error(content, question_note, text_pre, text_post):
    tag = question_note.tags[0]
    question_title = field_by_name(question_note.fields, 'qt')
    reference = field_by_name(question_note.fields, 'rf')
    raise ReferenceError(
        text_pre + content + '" to question "' + question_title +
        '" in map "' + tag + '" (reference "' + reference + '"). ' +
        text_post)


# Algorithm for synchronization was adopted from
# https://unterwaditzer.net/2016/sync-algorithm.html
class SmrSynchronizer:
    def __init__(self):
        self.col = mw.col
        self.note_manager = XNoteManager(col=mw.col)
        self.smr_world = mw.smr_world
        self.map_manager = None
        self.current_sheet_sync = None
        self.warnings = []
        self.translator = FieldTranslator()

    @property
    def col(self) -> Collection:
        return self._col

    @col.setter
    def col(self, value: Collection):
        self._col = value

    @property
    def note_manager(self) -> XNoteManager:
        return self._note_manager

    @note_manager.setter
    def note_manager(self, value: XNoteManager):
        self._note_manager = value

    @property
    def smr_world(self) -> XOntology:
        return self._smr_world

    @smr_world.setter
    def smr_world(self, value: XOntology):
        self._smr_world = value

    def synchronize(self):
        local = {f: self.note_manager.get_local(f) for f in self.xmind_files}
        status = {d['file']: d for d in self.status_manager.status}
        x_decks = set(local[x_id]['deck'] for x_id in local)
        for d in x_decks:
            self.onto = None
            for f in self.xmind_files:
                self.change_list = {}
                if f not in status:
                    importer = XmindImporter(col=self.note_manager.col, file=f)
                    # importer.initialize_import(deck_id=d, repair=False)
                    continue
                local_change = status[f]['ankiMod'] != local[f]['ankiMod']
                if status[f]['osMod'] != os_file_mods[f]:
                    self.map_manager = XManager(f)
                    for file in self.map_manager.referenced_files:
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

    def add_remote_a(self, q_content, q_id, remote, status, a_tag, import_dict):
        a_content = self.map_manager.get_node_content(a_tag)
        a_field = field_from_content(a_content)

        # Add answer to note fields
        a_index = get_topic_index(a_tag)
        if not import_dict['note']:
            import_dict['note'] = self.note_manager.get_note_from_q_id(q_id)
        if not import_dict['meta']:
            import_dict['meta'] = meta_from_fields(import_dict['note'].fields)
        import_dict['index_dict'][a_index] = {
            'a_id': a_tag['id'], 'field': a_field}
        import_dict['importer'] = self.maybe_add_media(
            a_content, import_dict['importer'])

        # Add answer to ontology
        if not q_content:
            q_content = content_from_field(field_by_name(
                import_dict['note'].fields, 'qt'))
        q_class = self.translator.class_from_content(q_content)
        rel_dict = get_rel_dict(
            aIndex=a_index,
            image=q_content['media']['image'],
            media=q_content['media']['media'],
            x_id=q_id,
            ref=field_by_name(import_dict['note'].fields, 'rf'),
            sortId=field_by_name(import_dict['note'].fields, 'id'),
            doc=self.map_manager.file,
            sheet=import_dict['meta']['sheetId'],
            tag=import_dict['note'].tags[0]
        )
        a_concept = self.onto.add_answer(
            a_id=a_tag['id'], answer_field=a_field, rel_dict=rel_dict,
            question_class=q_class)

        # Add answer to status
        # a_cards = self.note_manager.get_answer_cards(note.id)
        # local_a_dict = local_answer_dict(anki_mod = a_card[])
        status['answers'][a_tag['id']] = remote['answers'][a_tag['id']]
        return import_dict

    def add_remote_as(self, q_content, q_id, remote, status, import_dict):
        not_in_status = [a for a in remote['answers'] if a not in status[
            'answers']]
        for a_id in not_in_status:
            a_tag = self.map_manager.get_tag_by_id(a_id)
            import_dict = self.add_remote_a(
                import_dict=import_dict,
                q_content=q_content,
                q_id=q_id, remote=remote, status=status, a_tag=a_tag)
        return import_dict

    def change_answer(self, answer, question, local, status, import_dict):

        # Change answer in map
        title = title_from_field(local[answer]['content'])
        img = image_from_field(local[answer]['content'])
        x_id = answer
        self.map_manager.set_node_content(
            img=img, title=title, x_id=x_id,
            media_dir=self.note_manager.media_dir)

        # Change answer in Ontology
        self.onto.change_answer(q_id=question, a_id=answer,
                                a_field=local[answer]['content'])

        # Remember this change for final note adjustments
        self.change_list[self.current_sheet_sync].update(
            deep_merge(self.change_list[self.current_sheet_sync],
                       {question: {answer: change_dict(
                           old=status[answer]['content'],
                           new=local[answer]['content'])}}))

        # Change answer in status
        status[answer].update(local[answer])

    def change_remote_as(self, status, remote, q_id, level, import_dict):
        for a_id in {**status, **remote}:
            if not status[a_id]['xMod'] == remote[a_id]['xMod']:
                if not import_dict['note']:
                    note = self.note_manager.get_note_from_q_id(q_id)

                # Change answer in note
                a_content = self.map_manager.content_by_id(a_id)
                a_field = field_from_content(a_content)
                old_field = import_dict['note'].fields[get_index_by_a_id(
                    note=import_dict['note'], a_id=a_id)]
                if not a_field == old_field:
                    import_dict['note'].fields[
                        get_index_by_field_name('a' + str(
                            remote[a_id]['index']))] = a_field
                    old_content = content_from_field(old_field)
                    self.maybe_add_media(content=a_content,
                                         old_content=old_content,
                                         importer=import_dict['importer'])

                    # Change answer in ontology
                    self.onto.change_answer(q_id=q_id, a_id=a_id,
                                            a_field=a_field)

                    # Change answer content in status and xmod
                    status[a_id]['content'] = a_field

                    # Add change to ref_change_list
                    import_dict['ref_changes'][a_id] = change_dict(
                        old=old_field, new=a_field)
                status[a_id]['xMod'] = remote[a_id]['xMod']

                # If index has changed:
            if not status[a_id]['index'] == remote[a_id]['index']:

                # Change index in note
                if not import_dict['note']:
                    import_dict['note'] = \
                        self.note_manager.get_note_from_q_id(q_id)
                a_field = import_dict['note'].fields[get_index_by_a_id(
                    note=import_dict['note'], a_id=a_id)]
                a_content = content_from_field(a_field)
                a_class = self.translator.class_from_content(a_content)
                import_dict['index_dict'][remote[a_id]['index']] = a_field

                # Change index in ontology
                self.onto.set_trpl_a_index(a_id=a_id, q_id=q_id,
                                           a_index=remote[a_id]['index'])

                # Change index in status
                status[a_id]['index'] = remote[a_id]['index']

                # Add change to sort_id_changes
                new_sort_id = sort_id_from_order_number(remote[a_id]['index'])
                if not level:
                    q_topic = self.map_manager.get_tag_by_id(q_id)
                    level = len(self.map_manager.ref_and_sort_id(q_topic)[1])
                import_dict['sort_id_changes'][a_id] = change_dict(
                    old=level, new=new_sort_id)

        # Assign answer fields with new indices to note fields
        if import_dict['index_dict']:
            self.note_manager.rearrange_answers(
                note=import_dict['note'], index_dict=import_dict['index_dict'])

        return import_dict

    def process_note(self, q_id, status, remote, import_dict):
        q_content = None
        level = None
        if not status['xMod'] == remote['xMod']:
            note = self.note_manager.get_note_from_q_id(q_id)
            q_content = self.map_manager.content_by_id(q_id)
            new_q_field = field_from_content(q_content)
            q_index = get_index_by_field_name('qt')

            # Add change to changes dict
            import_dict['ref_changes']['question'] = change_dict(
                old=note.fields[q_index], new=new_q_field)

            # Change question field to new question
            note.fields[q_index] = new_q_field

            # Change question in ontology
            self.onto.change_question(x_id=q_id, new_question=new_q_field)

            # Adjust question in status
            status['xMod'] = remote['xMod']

        # Adjust index if it has changed
        if not status['index'] == remote['index']:
            q_topic = self.map_manager.get_tag_by_id(q_id)
            level = len(self.map_manager.ref_and_sort_id(q_topic)[1])
            new_sort_id = sort_id_from_order_number(remote['index'])

            # Add change to changes dict
            import_dict['sort_id_changes']['question'] = change_dict(
                old=level, new=new_sort_id)

            # Adjust index in status
            status['index'] = remote['index']

        # Add new answers if there are any
        # TODO: check whether answers meta is adjusted correctly
        import_dict = self.add_remote_as(
            q_content=q_content, q_id=q_id, remote=remote,
            status=status, import_dict=import_dict)

        # Remove old answers if there are any
        # TODO: check whether answers meta is adjusted correctly
        import_dict = self.remove_remote_as(
            status=status['answers'], remote=remote['answers'], q_id=q_id,
            import_dict=import_dict)

        # Change answers that have changed content
        import_dict = self.change_remote_as(
            status=status['answers'], remote=remote['answers'], q_id=q_id,
            level=level, import_dict=import_dict)

        # Change answer in note fields
        # Change answer in ontology
        # Change answer in status

        # Adjust answer index for answers that have changed position
        # Adjust ref of all following notes and set new fields
        # if note:
        #     if ref_changes:
        #         self.note_manager.update_ref(note=note, changes=ref_changes)
        #     if sort_id_changes:
        #         self.note_manager.update_sort_id(note=note,
        #                                          changes=sort_id_changes)
        #     # self.note_manager.set_fields(...)
        # if importer:
        #     importer.finish_import()
        # print('change note in anki and status and put changes in change_list')

    def change_remote_question(self, question, status, local):
        # Change question in map
        title = title_from_field(local[question]['content'])
        img = image_from_field(local[question]['content'])
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

    def maybe_add_media(self, content, importer, old_content=None):
        a_media = content['media']
        if old_content:
            old_media = old_content['media']
        else:
            old_media = a_media
        if a_media['image'] or a_media['media']:
            if not importer:
                importer = XmindImporter(col=self.note_manager.col,
                                         file=self.map_manager.file)
            if a_media['image'] and not a_media['image'] == old_media['image']:
                importer.images.append(a_media['image'])
            if a_media['media'] and not a_media['media'] == old_media['media']:
                importer.media.append(a_media['media'])
        return importer

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
                # importer.import_map(sheet=sheet, deck_id=deck_id)
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
        import_dicts = {}
        importer = None
        meta = None

        # Remove questions that were removed in map
        not_in_remote = [q for q in status if q not in remote]
        self.remove_questions(q_ids=not_in_remote, status=status)

        # Add questions that were added in map
        not_in_status = [q for q in remote if q not in status]
        tags_to_add = [self.map_manager.get_tag_by_id(q) for q in not_in_status]
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
                        q_content = self.map_manager.get_node_content(
                            seed_dict['parent_q'])
                        import_dict = {
                            'meta': meta_from_fields(note.fields),
                            'note': note,
                            'importer': importer,
                            'index_dict': {},
                            'ref_changes': {},
                            'sort_id_changes': {}}
                        import_dicts[seed_dict['parent_q'][
                            'id']] = self.add_remote_a(
                            q_content=q_content,
                            q_id=seed_dict['parent_q']['id'],
                            remote=remote[seed_dict['parent_q']['id']],
                            status=status[seed_dict['parent_q']['id']],
                            a_tag=a, import_dict=import_dict)['index_dict']
                        self.note_manager.save_note(note)
                importer.partial_import(
                    seed_topic=seed_dict['tag'], sheet_id=sheet_id,
                    deck_id=deck_id, parent_q=seed_dict['parent_q'],
                    parent_as=parent_as, onto=self.onto)
            importer.finish_import()

            # Add questions to status
            importer_status = next(
                f for f in importer.status_manager.status if
                f['file'] == self.map_manager.file)['sheets'][sheet_id][
                'questions']
            for q_id in importer_status:
                if q_id not in status:
                    status[q_id] = importer_status[q_id]

        for question in {**status, **remote}:
            if question in import_dicts:
                import_dict = import_dicts[question]
            else:
                import_dict = {'note': note,
                               'meta': meta,
                               'importer': importer,
                               'index_dict': {},
                               'ref_changes': {},
                               'sort_id_changes': {}}
            self.process_note(q_id=question, status=status[question],
                              remote=remote[question],
                              import_dict=import_dict)
        print()

    def remove_questions(self, q_ids, status):
        self.note_manager.remove_notes_by_q_ids(q_ids)
        self.onto.remove_questions(q_ids)
        for q_id in q_ids:
            del status[q_id]

    def remove_remote_as(self, status, remote, q_id, import_dict):
        not_in_remote = [a for a in status if a not in remote]
        for a_id in not_in_remote:

            # Remove answer from note fields
            if not import_dict['note']:
                import_dict['note'] = self.note_manager.get_note_from_q_id(q_id)
            import_dict['note'].fields[get_index_by_field_name(
                'a' + str(status[a_id]['index']))] = ''

            # Remove answer from ontology
            self.onto.remove_answer(q_id=q_id, a_id=a_id)

            # Remove answer from status
            del status[a_id]
        return import_dict

    def remove_sheet(self, sheet, status):
        self.note_manager.remove_sheet(sheet)
        del status[sheet]
        self.onto.remove_sheet(sheet)
