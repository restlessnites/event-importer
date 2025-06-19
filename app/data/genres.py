"""Genre definitions and validation utilities."""

from __future__ import annotations

import re


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
        "hardcore punk": "hardcore",
        "metalcore": "metal",
        "deathcore": "death metal",
        "black metal": "metal",
        "doom": "doom metal",
        "stoner": "stoner rock",
        "post rock": "post-rock",
        "math rock": "math rock",
        "hip-hop": "hip hop",
        "rap music": "rap",
        "trap music": "trap",
        "old school": "old school hip hop",
        "conscious rap": "conscious hip hop",
        "gangsta": "gangsta rap",
        "r'n'b": "r&b",
        "rnb": "r&b",
        "rhythm & blues": "r&b",
        "soul music": "soul",
        "funk music": "funk",
        "disco music": "disco",
        "reggae music": "reggae",
        "world": "world music",
        "folk music": "folk",
        "country music": "country",
        "bluegrass music": "bluegrass",
        "latin music": "latin",
        "afro": "afrobeat",
        "african": "afrobeat",
    }

    @classmethod
    def normalize_genre(cls: type[MusicGenres], genre: str) -> str:
        """Normalize a genre string."""
        if not genre:
            return ""

        # Clean up
        cleaned = genre.lower().strip()

        # Remove common suffixes
        cleaned = re.sub(r"\s*music$", "", cleaned)
        cleaned = re.sub(r"\s*genre$", "", cleaned)

        # Check aliases first
        if cleaned in cls.ALIASES:
            return cls.ALIASES[cleaned]

        # Check if it's already a known genre
        if cleaned in cls.ALL_GENRES:
            return cleaned

        # Check for partial matches
        for known_genre in cls.ALL_GENRES:
            if cleaned in known_genre or known_genre in cleaned:
                return known_genre

        return cleaned

    @classmethod
    def validate_genres(cls: type[MusicGenres], genres: list[str]) -> list[str]:
        """Validate and normalize a list of genres."""
        validated = []
        seen = set()

        for genre in genres:
            normalized = cls.normalize_genre(genre)
            if normalized and normalized in cls.ALL_GENRES and normalized not in seen:
                seen.add(normalized)
                validated.append(normalized.title())  # Return with proper casing

        return validated

    @classmethod
    def get_category(cls: type[MusicGenres], genre: str) -> str:
        """Get the category for a genre."""
        normalized = cls.normalize_genre(genre)

        if normalized in cls.ELECTRONIC:
            return "Electronic"
        elif normalized in cls.ROCK:
            return "Rock"
        elif normalized in cls.HIP_HOP:
            return "Hip Hop"
        elif normalized in cls.JAZZ:
            return "Jazz"
        elif normalized in cls.POP_RNB:
            return "Pop/R&B"
        elif normalized in cls.WORLD_FOLK:
            return "World/Folk"
        elif normalized in cls.CLASSICAL:
            return "Classical"
        elif normalized in cls.EXPERIMENTAL:
            return "Experimental"
        else:
            return "Other"
