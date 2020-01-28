from .xmanager import XManager, get_os_mod
from .xnotemanager import *
from .statusmanager import StatusManager
from .consts import USER_PATH
from .xontology import XOntology


# Algorithm for synchronization was adopted from
# https://unterwaditzer.net/2016/sync-algorithm.html
class XSyncer():
    def __init__(self, col, status_file=None):
        self.col = col
        self.note_manager = XNoteManager(col=col)
        self.xmind_files = self.note_manager.get_xmind_files()
        self.map_manager = None
        self.onto = None
        self.status_manager = StatusManager(status_file=status_file)
        self.change_list = None

    def run(self):
        local = {f: self.note_manager.get_local(f) for f in self.xmind_files}
        os_file_mods = {f: get_os_mod(f) for f in self.xmind_files}
        status = {d['file']: d for d in self.status_manager.status}
        x_decks = set(local[l]['deck'] for l in local)
        for d in x_decks:
            self.onto = None
            for f in self.xmind_files:
                self.change_list = dict()
                local_change = status[f]['ankiMod'] != local[f]['ankiMod']
                if status[f]['osMod'] != os_file_mods[f]:
                    self.map_manager = XManager(f)
                    remote = self.map_manager.get_remote()
                    remote_change = status[f]['xMod'] != remote['xMod']
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
                elif not local_change and remote_change:
                    print('')
                else:
                    print('')

    def process_change_list(self):
        print('TODO')

    def process_local_answers(self, status, local, question):
        sort_id = None
        for answer in {**local, **status}:
            if answer not in local:
                print('remove answer from map')
            elif answer not in status:
                print('add answer to map')
                continue
            elif not status[answer]['content'] == local[answer]['content']:
                title = title_from_field(local[answer]['content'])
                img = img_from_field(local[answer]['content'])
                answer_tag = self.map_manager.getTagById(answer)
                self.map_manager.set_node_content(
                    tag=answer_tag, title=title, img=img,
                    media_dir=self.note_manager.media_dir)
            else:
                continue
            if not sort_id:
                sort_id = self.note_manager.get_field_by_name(
                    self.note_manager.get_flds_from_qId(question), 'id')
            self.change_list[sort_id] = title


    def process_local_changes(self, status, local):
        for sheet in {**local, **status}:
            if local[sheet]['ankiMod'] != status[sheet][
                    'ankiMod']:
                self.process_local_questions(status=status[sheet]['questions'],
                                             local=local[sheet]['questions'])

    def process_local_questions(self, status, local):
        for question in {**local, **status}:
            local_field = local[question]['content']
            if local_field != status[question]['content']:
                title = title_from_field(local_field)
                img = img_from_field(local_field)
                # Export changed question to xmind
                question_tag = self.map_manager.getTagById(question)
                self.map_manager.set_node_content(
                    tag=question_tag, title=title, img=img,
                    media_dir=self.note_manager.media_dir)
                # Change question in ontology
                self.onto.change_question(x_id=question,
                                          new_question=local_field)
                # Remember this change for final note adjustments
                sort_id = self.note_manager.get_field_by_name(
                    self.note_manager.get_flds_from_qId(question), 'id')
                self.change_list[sort_id] = local_field
            self.process_local_answers(status=status[question]['answers'],
                                       local=local[question]['answers'],
                                       question=question)
            print()
