from dataclasses import dataclass, field
from typing import List
from play import Play, ReadingMetadata

@dataclass
class Announcement:
    key: List[str]
    text: str

    def key_as_filename(self) -> str:
        return "-".join(self.key)

@dataclass
class Announcer:
    play: Play
    announcer_role: str = "_ANNOUNCER"
    metadata: ReadingMetadata = field(init=False)

    def __post_init__(self) -> None:
        self.metadata = self.play.get_reading_metadata_for_role(self.announcer_role)
        

    def title_announcement(self) -> Announcement:
        return Announcement(
            ["title"],
            f'{self.play.title}, by {self.play.author}.'
        )
    
    def author_announcement(self) -> Announcement:
        return Announcement(
            ["author"],
            self.play.author
        )
    
    def by_author_announcement(self) -> Announcement:
        return Announcement(
            ["by"],
            "by {self.play.author}"
        )
    
    def original_publication_date_announcement(self) -> Announcement:
        year = self.play.source_text_metadata.original_publication_year
        if year:
            text = f"originally published in {year}."
        else:
            text = "original publication date unknown."
        return Announcement(
            ["original_publication_date"],
            text
        )
    
    def end_of_recording_announcement(self) -> Announcement:
        return Announcement(
            ["end_of_recording"],
            f'End of "{self.play.title}" by {self.play.author}'
        )
    
    def announcements(self) -> List[Announcement]:
        return [
            self.title_announcement(),
            self.author_announcement(),
            self.by_author_announcement(),
            self.original_publication_date_announcement(),
            self.end_of_recording_announcement()
        ]
    
def LibrivoxAnnouncer(Announcer):

    def this_is_a_librivox_recording(self) -> Announcement:
        return Announcement(
            ["librivox", "this_is_a_librivox_recording"], 
            "This is a Librivox Recording."
            )

    def all_librivox_recordings(self) -> Announcement:
        return Announcement(
            ["librivox", "all_librivox_recordings"],
            "All Librivox Recordings are in the public domain."
        )

    def for_more_information(self) -> Announcement:
        return Announcement(
            ["librivox", "for_more_information"],
            "For more information or to volunteer, please visit librivox.org."
        )

    def section_pd_declaration(self) -> Announcement:
        return Announcement(
            ["librivox", "section_pd_declaration"],
            "This librivox recording is in the public domain."
        )

    def section_end_suffix(self) -> Announcement:
        return Announcement(
            ["librivox", "section_end_suffix"],
            f"of \"{self.play.title}\" by {self.play.author}"
        )

    def section_start_announcement(self, section_number: int) -> Announcement:
        return Announcement(
            ["librivox", 
             "sections", 
             str(section_number),
             "end"], 
             f"section{section_number}",
        )
    
    def section_end_announcement(self, section_number: int) -> Announcement:
        return Announcement(
            ["librivox", 
             "sections", 
             str(section_number), 
            "end"],
             f"end of section {section_number}",
        )
    
    def section_announcements(self) -> List[Announcement]:
        anouncements = []
        for s in range(self.play.first_section, self.play.last_section + 1):
            anouncements.extend(self.section_start_announcement(s))
            anouncements.extend(self.section_end_announcement(s))
        return anouncements
    
    def announcements(self) -> List[Announcement]:
        base_announcements = super().announcements()
        librivox_announcements = [
            self.this_is_a_librivox_recording(),
            self.all_librivox_recordings(),
            self.for_more_information(),
            self.section_pd_declaration(),
            self.section_end_suffix()
        ]
        return base_announcements + librivox_announcements + self.section_announcements()
    