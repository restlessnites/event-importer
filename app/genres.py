"""Genre definitions and validation utilities."""

from __future__ import annotations


class MusicGenres:
    """Music genre definitions and validation utilities."""

    # Core genre categories
    ELECTRONIC = {
        "electronic",
        "house",
        "techno",
        "trance",
        "drum and bass",
        "dubstep",
        "ambient",
        "downtempo",
        "breakbeat",
        "garage",
        "jungle",
        "hardcore",
        "industrial",
        "edm",
        "bass music",
        "uk garage",
        "grime",
        "footwork",
        "dnb",
        "d&b",
        "electro",
        "minimal",
        "deep house",
        "tech house",
        "progressive house",
        "tribal",
        "acid house",
        "hardstyle",
        "gabber",
    }

    ROCK = {
        "rock",
        "indie rock",
        "alternative rock",
        "punk rock",
        "hard rock",
        "progressive rock",
        "psychedelic rock",
        "garage rock",
        "post-punk",
        "shoegaze",
        "grunge",
        "metal",
        "heavy metal",
        "death metal",
        "black metal",
        "doom metal",
        "thrash metal",
        "metalcore",
        "post-rock",
        "math rock",
        "emo",
        "post-hardcore",
        "screamo",
        "noise rock",
        "stoner rock",
    }

    HIP_HOP = {
        "hip hop",
        "rap",
        "trap",
        "boom bap",
        "conscious hip hop",
        "drill",
        "mumble rap",
        "old school hip hop",
        "gangsta rap",
        "underground hip hop",
        "experimental hip hop",
        "lo-fi hip hop",
        "phonk",
        "crunk",
    }

    JAZZ = {
        "jazz",
        "bebop",
        "smooth jazz",
        "jazz fusion",
        "free jazz",
        "acid jazz",
        "cool jazz",
        "hard bop",
        "post-bop",
        "avant-garde jazz",
        "latin jazz",
        "swing",
        "big band",
        "ragtime",
        "nu jazz",
    }

    POP_RNB = {
        "pop",
        "r&b",
        "soul",
        "funk",
        "disco",
        "motown",
        "contemporary r&b",
        "neo-soul",
        "gospel",
        "blues",
        "rhythm and blues",
        "doo-wop",
        "new jack swing",
        "quiet storm",
    }

    WORLD_FOLK = {
        "world music",
        "folk",
        "country",
        "bluegrass",
        "reggae",
        "afrobeat",
        "latin",
        "salsa",
        "cumbia",
        "reggaeton",
        "bossa nova",
        "samba",
        "flamenco",
        "celtic",
        "traditional",
        "ethnic",
        "tribal",
    }

    CLASSICAL = {
        "classical",
        "orchestral",
        "chamber music",
        "opera",
        "contemporary classical",
        "baroque",
        "romantic",
        "impressionist",
        "modern classical",
        "minimalist",
        "symphonic",
        "choral",
        "string quartet",
    }

    EXPERIMENTAL = {
        "experimental",
        "noise",
        "avant-garde",
        "drone",
        "field recordings",
        "sound art",
        "musique concrète",
        "electroacoustic",
        "improvisation",
        "free improvisation",
        "glitch",
        "microsound",
    }

    # All genres combined
    ALL_GENRES = (
        ELECTRONIC
        | ROCK
        | HIP_HOP
        | JAZZ
        | POP_RNB
        | WORLD_FOLK
        | CLASSICAL
        | EXPERIMENTAL
    )

    # Genre aliases and variations
    ALIASES = {
        "edm": "electronic",
        "dance": "electronic",
        "club": "electronic",
        "electronica": "electronic",
        "dnb": "drum and bass",
        "d&b": "drum and bass",
        "dub": "dubstep",
        "hardcore techno": "hardcore",
        "uk garage": "garage",
        "2-step": "garage",
        "alternative": "alternative rock",
        "alt rock": "alternative rock",
        "indie": "indie rock",
        "punk": "punk rock",
        "metal": "heavy metal",
        "death": "death metal",
        "black": "black metal",
        "doom": "doom metal",
        "thrash": "thrash metal",
        "core": "metalcore",
        "post": "post-rock",
        "math": "math rock",
        "hardcore": "post-hardcore",
        "screamo": "post-hardcore",
        "noise music": "noise rock",
        "stoner": "stoner rock",
        "hip-hop": "hip hop",
        "hiphop": "hip hop",
        "trap": "trap",
        "boom": "boom bap",
        "conscious": "conscious hip hop",
        "drill": "drill",
        "mumble": "mumble rap",
        "old school": "old school hip hop",
        "gangsta": "gangsta rap",
        "underground": "underground hip hop",
        "experimental hip": "experimental hip hop",
        "lo-fi": "lo-fi hip hop",
        "lofi": "lo-fi hip hop",
        "phonk": "phonk",
        "crunk": "crunk",
        "bebop": "bebop",
        "smooth": "smooth jazz",
        "fusion": "jazz fusion",
        "free": "free jazz",
        "acid": "acid jazz",
        "cool": "cool jazz",
        "hard": "hard bop",
        "post-bop": "post-bop",
        "swing": "swing",
        "big": "big band",
        "ragtime": "ragtime",
        "nu": "nu jazz",
        "r&b": "r&b",
        "soul": "soul",
        "funk": "funk",
        "disco": "disco",
        "motown": "motown",
        "contemporary": "contemporary r&b",
        "neo": "neo-soul",
        "gospel": "gospel",
        "blues": "blues",
        "rhythm": "rhythm and blues",
        "doo-wop": "doo-wop",
        "new jack": "new jack swing",
        "quiet": "quiet storm",
        "world": "world music",
        "folk": "folk",
        "country": "country",
        "bluegrass": "bluegrass",
        "reggae": "reggae",
        "afrobeat": "afrobeat",
        "latin": "latin",
        "salsa": "salsa",
        "cumbia": "cumbia",
        "reggaeton": "reggaeton",
        "bossa": "bossa nova",
        "samba": "samba",
        "flamenco": "flamenco",
        "celtic": "celtic",
        "traditional": "traditional",
        "ethnic": "ethnic",
        "tribal": "tribal",
        "classical": "classical",
        "orchestral": "orchestral",
        "chamber": "chamber music",
        "opera": "opera",
        "contemporary classical": "contemporary classical",
        "baroque": "baroque",
        "romantic": "romantic",
        "impressionist": "impressionist",
        "modern": "modern classical",
        "minimalist": "minimalist",
        "symphonic": "symphonic",
        "choral": "choral",
        "string": "string quartet",
        "experimental": "experimental",
        "noise": "noise",
        "avant-garde music": "avant-garde",
        "drone": "drone",
        "field": "field recordings",
        "sound": "sound art",
        "musique": "musique concrète",
        "electroacoustic": "electroacoustic",
        "improvisation": "improvisation",
        "free improvisation": "free improvisation",
        "glitch": "glitch",
        "microsound": "microsound",
    }

    # Genre categories mapping
    CATEGORIES = {
        "electronic": ELECTRONIC,
        "rock": ROCK,
        "hip hop": HIP_HOP,
        "jazz": JAZZ,
        "pop/r&b": POP_RNB,
        "world/folk": WORLD_FOLK,
        "classical": CLASSICAL,
        "experimental": EXPERIMENTAL,
    }

    @classmethod
    def normalize_genre(cls: type[MusicGenres], genre: str) -> str:
        """Normalize a genre string to a standard format."""
        if not genre:
            return ""

        # Convert to lowercase and strip whitespace
        normalized = genre.lower().strip()

        # Check if it's an alias
        if normalized in cls.ALIASES:
            return cls.ALIASES[normalized]

        # Check if it's already a valid genre
        if normalized in cls.ALL_GENRES:
            return normalized

        # Try to find a close match
        for valid_genre in cls.ALL_GENRES:
            if normalized == valid_genre or normalized in valid_genre or valid_genre in normalized:
                return valid_genre

        # If no match found, return the original (normalized)
        return normalized

    @classmethod
    def validate_genres(cls: type[MusicGenres], genres: list[str]) -> list[str]:
        """Validate and normalize a list of genres."""
        if not genres:
            return []

        validated = []
        for genre in genres:
            normalized = cls.normalize_genre(genre)
            if normalized and normalized in cls.ALL_GENRES:
                validated.append(normalized)

        return list(set(validated))  # Remove duplicates

    @classmethod
    def get_category(cls: type[MusicGenres], genre: str) -> str:
        """Get the category for a given genre."""
        normalized = cls.normalize_genre(genre)

        for category, genres in cls.CATEGORIES.items():
            if normalized in genres:
                return category

        return "other"
