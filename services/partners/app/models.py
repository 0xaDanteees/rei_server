from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, DateTime, Boolean, Float, Integer, Text, ForeignKey, Index, func, text, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨
#                       ENUMS
# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"
    CUSTOM = "custom"

class Etnicity(str, Enum):
    """
    Etnicity enum representing diverse ethnicities.
    """
    LATINO_HISPANIC = "latino_hispanic"
    ASIAN = "asian"
    BLACK_AFRICAN = "black_african"
    WHITE_CAUCAUSIAN = "white_caucasian"
    NATIVE_AMERICAN = "native_american"
    EAST_EUROPEAN = "east_european"
    EAST_ASIAN = "east_asian"
    SOUTH_ASIAN = "south_asian"
    MIDDLE_EASTERN = "middle_eastern"
    AFRICAN = "african"
    CARIBBEAN = "caribbean"
    INDIGENOUS = "indigenous"
    INDHUSIAN = "indhusian"
    AUSTRALIAN = "australian"
    PACIFIC_ISLANDER = "pacific_islander"
    RED_NORTHERN = "red_northern"
    RED_SOUTHERN = "red_southern"
    RED_EASTERN = "red_eastern"
    RED_WESTERN = "red_western"
    AMERICAN_INDIAN = "american_indian"
    AMERICAN_HAWAIIAN = "american_hawaiian"
    AMERICAN_ALASKAN = "american_alaskan"
    RUSSIAN = "russian"
    ARABIC = "arabic"

class SkinTone(str, Enum):
    """
    Skin tone enum representing diverse ethnicities with Pantone-inspired color codes.
    Colors are approximated to represent the beautiful diversity of human skin tones.
    """
    # European/Caucasian tones
    FAIR_IVORY = "#F7E7CE"          # Very light, cool undertones
    LIGHT_BEIGE = "#F3D5AB"         # Light with warm undertones
    MEDIUM_PEACH = "#E8B891"        # Medium with peachy undertones
    OLIVE_TAN = "#D4A574"           # Mediterranean/olive complexion
    
    # East Asian tones
    PORCELAIN = "#F5E6D3"           # Very light with yellow undertones
    WARM_IVORY = "#F0D0A0"          # Light with golden undertones
    GOLDEN_BEIGE = "#E6C2A6"        # Medium with golden undertones
    HONEY_WHEAT = "#D4A484"         # Warm medium tone
    
    # South Asian tones
    WARM_SAND = "#C89F7E"           # Light brown with warm undertones
    CARAMEL = "#B08862"             # Medium caramel tone
    GOLDEN_BROWN = "#A67C52"        # Rich golden brown
    DEEP_BRONZE = "#8B5A3C"         # Deep bronze tone
    
    # Middle Eastern/North African tones
    DESERT_SAND = "#C49484"         # Light with reddish undertones
    WARM_AMBER = "#B5845F"          # Medium amber tone
    RICH_COPPER = "#9A6B47"         # Rich copper brown
    DEEP_OLIVE = "#7D5A40"          # Deep olive brown
    
    # African/Afro-Caribbean tones
    WARM_COCOA = "#8D5524"          # Medium brown with warm undertones
    RICH_MOCHA = "#6F4518"          # Rich mocha brown
    DEEP_MAHOGANY = "#5D3317"       # Deep mahogany
    DARK_CHOCOLATE = "#4A2C17"      # Dark chocolate brown
    DEEP_ESPRESSO = "#3C1A0F"       # Very deep brown
    EBONY = "#2D1609"               # Deep ebony tone
    
    # Latino/Hispanic tones (diverse range)
    WARM_VANILLA = "#F2D7B3"        # Light with warm undertones
    GOLDEN_TAN = "#D4B896"          # Golden tan
    CINNAMON = "#B8956A"            # Medium cinnamon
    CAFE_AU_LAIT = "#9D7A54"        # Coffee with milk tone
    DEEP_SIENNA = "#7A5C42"         # Deep sienna brown
    
    # Indigenous tones
    TERRA_COTTA = "#B5825A"         # Earthy terra cotta
    RUSSET = "#A0724B"              # Russet brown
    CEDAR = "#8B653F"               # Cedar wood tone

class EyeShape(str, Enum):
    ROUND = "round"
    ALMOND = "almond"
    OVAL = "oval"
    CAT = "cat"
    HUMAN = "human"
    HOODED = "hooded"
    UPTURNED = "upturned"
    DOWNTURNED = "downturned"
    MONOLID = "monolid"

class EyeSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class HairStyle(str, Enum):
    BALD = "bald"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    CURLY = "curly"
    WAVY = "wavy"
    STRAIGHT = "straight"
    AFRO = "afro"
    PONYTAIL = "ponytail"
    BRAIDS = "braids"
    BUZZ_CUT = "buzz_cut"

class MouthShape(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    THIN = "thin"
    FULL = "full"
    HEART = "heart"

class NoseShape(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    STRAIGHT = "straight"
    ROMAN = "roman"
    BUTTON = "button"
    HOOKED = "hooked"

class NoseSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class EarShape(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ROUND = "round"
    POINTED = "pointed"

class EarSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class EarPosition(str, Enum):
    STRAIGHT = "straight"
    ANGLED = "angled"
    HIGH = "high"
    LOW = "low"

class EarHair(str, Enum):
    NONE = "none"
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"

class EarHairLength(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

class EarHairStyle(str, Enum):
    NONE = "none"
    STRAIGHT = "straight"
    CURLY = "curly"
    WAVY = "wavy"

class EarHairPosition(str, Enum):
    STRAIGHT = "straight"
    ANGLED = "angled"
    FORWARD = "forward"
    BACKWARD = "backward"

class FaceShape(str, Enum):
    OVAL = "oval"
    ROUND = "round"
    SQUARE = "square"
    HEART = "heart"
    DIAMOND = "diamond"
    OBLONG = "oblong"

class BodyType(str, Enum):
    SLIM = "slim"
    ATHLETIC = "athletic"
    AVERAGE = "average"
    CURVY = "curvy"
    PLUS_SIZE = "plus_size"

class FitnessLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    AVERAGE = "average"
    HIGH = "high"
    VERY_HIGH = "very_high"

class ClothingSize(str, Enum):
    """
    Clothing size enum representing diverse clothing sizes.
    XX sizes we need to be careful with...
    """
    XXS = "xxs"
    XS = "xs"
    S = "s"
    M = "m"
    L = "l"
    XL = "xl"
    XXL = "xxl"
    XXXL = "xxxl"
    XXXXL = "xxxxl"

class TattooLocation(str, Enum):
    ARM = "arm"
    FOREARM = "forearm"
    SHOULDER = "shoulder"
    BACK = "back"
    CHEST = "chest"
    LEG = "leg"
    ANKLE = "ankle"
    NECK = "neck"
    WRIST = "wrist"

class BeardStyle(str, Enum):
    NONE = "none"
    FULL_BEARD = "full_beard"
    GOATEE = "goatee"
    MUSTACHE = "mustache"
    SOUL_PATCH = "soul_patch"
    STUBBLE = "stubble"

class BeardPosition(str, Enum):
    NONE = "none"
    CENTERED = "centered"
    LEFT = "left"
    RIGHT = "right"

class MoustacheStyle(str, Enum):
    NONE = "none"
    CLASSIC = "classic"
    HANDLEBAR = "handlebar"
    PENCIL = "pencil"
    WALRUS = "walrus"

class MoustachePosition(str, Enum):
    NONE = "none"
    CENTERED = "centered"
    LEFT = "left"
    RIGHT = "right"

class EyeBrowStyle(str, Enum):
    NONE = "none"
    NATURAL = "natural"
    ARCHED = "arched"
    STRAIGHT = "straight"
    THICK = "thick"
    THIN = "thin"

class EyeBrowPosition(str, Enum):
    NONE = "none"
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"

class PiercingLocation(str, Enum):
    EAR_LOBE = "ear_lobe"
    EAR_CARTILAGE = "ear_cartilage"
    NOSE = "nose"
    SEPTUM = "septum"
    EYEBROW = "eyebrow"
    LIP = "lip"
    TONGUE = "tongue"
    NAVEL = "navel"

# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨
#                       SQLALCHEMY MODELS
# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨

class Partner(Base):
    __tablename__ = "partners"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Basic info
    name = Column(String(128), nullable=False)
    user_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gender = Column(String(50), nullable=False, default=Gender.FEMALE)
    age = Column(Integer, nullable=False, default=18)
    
    # Appearance
    skin_tone = Column(String(10), nullable=False, default=SkinTone.FAIR_IVORY)
    body_type = Column(String(50), nullable=False, default=BodyType.AVERAGE)
    height = Column(Integer, nullable=False, default=170)  # in cm
    fitness_level = Column(String(50), nullable=False, default=FitnessLevel.AVERAGE)

    # Face
    face_shape = Column(String(50), nullable=False, default=FaceShape.OVAL)
    eye_shape = Column(String(50), nullable=False, default=EyeShape.HUMAN)
    eye_size = Column(String(50), nullable=False, default=EyeSize.MEDIUM)
    eye_color = Column(String(10), nullable=False, default="#8B4513")
    nose_shape = Column(String(50), nullable=False, default=NoseShape.STRAIGHT)
    nose_size = Column(String(50), nullable=False, default=NoseSize.MEDIUM)
    nose_color = Column(String(10), nullable=False, default="#FDBCB4")
    hair_color = Column(String(10), nullable=False, default="#8B4513")
    hair_style = Column(String(50), nullable=False, default=HairStyle.STRAIGHT)
    mouth_shape = Column(String(50), nullable=False, default=MouthShape.SMALL)
    teeth_color = Column(String(10), nullable=False, default='#FFFFFF')
    lip_color = Column(String(10), nullable=False, default='#FF69B4')
    
    # Ears
    ear_shape = Column(String(50), nullable=False, default=EarShape.SMALL)
    ear_size = Column(String(50), nullable=False, default=EarSize.MEDIUM)
    ear_color = Column(String(10), nullable=False, default='#FDBCB4')
    ear_position = Column(String(50), nullable=False, default=EarPosition.STRAIGHT)
    ear_hair = Column(String(50), nullable=False, default=EarHair.NONE)
    ear_hair_color = Column(String(10), nullable=False, default='#8B4513')
    ear_hair_length = Column(String(50), nullable=False, default=EarHairLength.SHORT)
    ear_hair_style = Column(String(50), nullable=False, default=EarHairStyle.NONE)
    ear_hair_position = Column(String(50), nullable=False, default=EarHairPosition.STRAIGHT)

    # Body proportions (using float 0.0-1.0 scale)
    leg_length = Column(Float, nullable=False, default=0.5)
    arm_length = Column(Float, nullable=False, default=0.5)
    torso_length = Column(Float, nullable=False, default=0.5)
    gluteal_size = Column(Float, nullable=False, default=0.5)
    chest_size = Column(Float, nullable=False, default=0.5)
    hand_size = Column(Float, nullable=False, default=0.5)
    foot_size = Column(Float, nullable=False, default=0.5)
    waist_size = Column(Float, nullable=False, default=0.5)
    neck_size = Column(Float, nullable=False, default=0.5)

    # Nails
    nail_length = Column(Float, nullable=False, default=0.5)
    nail_color = Column(String(10), nullable=False, default='#FFC0CB')
    foot_nail_length = Column(Float, nullable=False, default=0.5)
    foot_nail_color = Column(String(10), nullable=False, default='#FFC0CB')

    # Facial features
    has_freckles = Column(Boolean, nullable=False, default=False)
    has_beauty_marks = Column(Boolean, nullable=False, default=False)
    has_wrinkles = Column(Boolean, nullable=False, default=False)
    has_moles = Column(Boolean, nullable=False, default=False)

    # Facial hair
    has_beard = Column(Boolean, nullable=False, default=False)
    has_moustache = Column(Boolean, nullable=False, default=False)
    has_eyebrows = Column(Boolean, nullable=False, default=True)
    beard_color = Column(String(10), nullable=False, default='#8B4513')
    moustache_color = Column(String(10), nullable=False, default='#8B4513')
    eyebrow_color = Column(String(10), nullable=False, default='#8B4513')
    beard_length = Column(Float, nullable=False, default=0.0)
    moustache_length = Column(Float, nullable=False, default=0.0)
    eyebrow_length = Column(Float, nullable=False, default=0.5)
    beard_style = Column(String(50), nullable=False, default=BeardStyle.NONE)
    moustache_style = Column(String(50), nullable=False, default=MoustacheStyle.NONE)
    eyebrow_style = Column(String(50), nullable=False, default=EyeBrowStyle.NATURAL)
    beard_position = Column(String(50), nullable=False, default=BeardPosition.NONE)
    moustache_position = Column(String(50), nullable=False, default=MoustachePosition.NONE)
    eyebrow_position = Column(String(50), nullable=False, default=EyeBrowPosition.NORMAL)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    clothing_items = relationship("PartnerClothing", back_populates="partner", cascade="all, delete-orphan")
    tattoos = relationship("PartnerTattoo", back_populates="partner", cascade="all, delete-orphan")
    piercings = relationship("PartnerPiercing", back_populates="partner", cascade="all, delete-orphan")

class ClothingItem(Base):
    __tablename__ = "clothing_items"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    name = Column(String(128), nullable=False)
    category = Column(String(128), nullable=False)  # top, bottom, etc
    sub_category = Column(String(128), nullable=True)  # t-shirt, jeans, etc
    color = Column(String(10), nullable=False)
    size = Column(String(10), nullable=False, default=ClothingSize.M)
    price = Column(Float, nullable=False, default=0.0)
    image_url = Column(String(255), nullable=True)
    is_available = Column(Boolean, nullable=False, default=True)
    is_premium = Column(Boolean, nullable=False, default=False)
    is_gift = Column(Boolean, nullable=False, default=False)
    is_bought = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    bought_at = Column(DateTime(timezone=True), nullable=True)
    dropped_at = Column(DateTime(timezone=True), nullable=True)
    gifted_at = Column(DateTime(timezone=True), nullable=True)

class PartnerClothing(Base):
    __tablename__ = "partner_clothing"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    partner_id = Column(PGUUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    clothing_item_id = Column(PGUUID(as_uuid=True), ForeignKey("clothing_items.id"), nullable=False)
    
    is_equipped = Column(Boolean, nullable=False, default=False)
    slot = Column(String(50), nullable=False)  # top, bottom, etc

    partner = relationship("Partner", back_populates="clothing_items")
    clothing_item = relationship("ClothingItem")

class PartnerPiercing(Base):
    __tablename__ = "partner_piercings"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    partner_id = Column(PGUUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    location = Column(String(50), nullable=False)
    jewelry_type = Column(String(50), nullable=False)
    jewelry_material = Column(String(50), nullable=False)
    jewelry_color = Column(String(10), nullable=False)
    size = Column(String(50), nullable=False, default="medium")

    partner = relationship("Partner", back_populates="piercings")

class PartnerTattoo(Base):
    __tablename__ = "partner_tattoos"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    partner_id = Column(PGUUID(as_uuid=True), ForeignKey("partners.id"), nullable=False)
    location = Column(String(50), nullable=False)
    tattoo_type = Column(String(50), nullable=False)
    tattoo_style = Column(String(50), nullable=False)
    tattoo_color = Column(String(10), nullable=False)
    size = Column(String(50), nullable=False)
    image_url = Column(String(255), nullable=True)

    partner = relationship("Partner", back_populates="tattoos")

# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨
#                       PYDANTIC SCHEMAS
# >w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨>w<¨

class PartnerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    gender: Gender = Gender.FEMALE
    age: int = Field(default=18, ge=18, le=100)
    skin_tone: SkinTone = SkinTone.FAIR_IVORY
    body_type: BodyType = BodyType.AVERAGE
    height: int = Field(default=170, ge=120, le=266)  # in cm
    fitness_level: FitnessLevel = FitnessLevel.AVERAGE
    
    # Face
    face_shape: FaceShape = FaceShape.OVAL
    eye_shape: EyeShape = EyeShape.HUMAN
    eye_size: EyeSize = EyeSize.MEDIUM
    eye_color: str = Field(default="#8B4513", pattern=r"^#[0-9A-F]{6}$")
    nose_shape: NoseShape = NoseShape.STRAIGHT
    nose_size: NoseSize = NoseSize.MEDIUM
    nose_color: str = Field(default="#FDBCB4", pattern=r"^#[0-9A-F]{6}$")
    hair_color: str = Field(default="#8B4513", pattern=r"^#[0-9A-F]{6}$")
    hair_style: HairStyle = HairStyle.STRAIGHT
    mouth_shape: MouthShape = MouthShape.SMALL
    teeth_color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-F]{6}$")
    lip_color: str = Field(default="#FF69B4", pattern=r"^#[0-9A-F]{6}$")
    
    # Ears
    ear_shape: EarShape = EarShape.SMALL
    ear_size: EarSize = EarSize.MEDIUM
    ear_color: str = Field(default="#FDBCB4", pattern=r"^#[0-9A-F]{6}$")
    ear_position: EarPosition = EarPosition.STRAIGHT
    ear_hair: EarHair = EarHair.NONE
    ear_hair_color: str = Field(default="#8B4513", pattern=r"^#[0-9A-F]{6}$")
    ear_hair_length: EarHairLength = EarHairLength.SHORT
    ear_hair_style: EarHairStyle = EarHairStyle.NONE
    ear_hair_position: EarHairPosition = EarHairPosition.STRAIGHT
    
    # Body proportions (0.0 to 1.0 scale)
    leg_length: float = Field(default=0.5, ge=0.0, le=1.0)
    arm_length: float = Field(default=0.5, ge=0.0, le=1.0)
    torso_length: float = Field(default=0.5, ge=0.0, le=1.0)
    gluteal_size: float = Field(default=0.5, ge=0.0, le=1.0)
    chest_size: float = Field(default=0.5, ge=0.0, le=1.0)
    hand_size: float = Field(default=0.5, ge=0.0, le=1.0)
    foot_size: float = Field(default=0.5, ge=0.0, le=1.0)
    waist_size: float = Field(default=0.5, ge=0.0, le=1.0)
    neck_size: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Nails
    nail_length: float = Field(default=0.5, ge=0.0, le=1.0)
    nail_color: str = Field(default="#FFC0CB", pattern=r"^#[0-9A-F]{6}$")
    foot_nail_length: float = Field(default=0.5, ge=0.0, le=1.0)
    foot_nail_color: str = Field(default="#FFC0CB", pattern=r"^#[0-9A-F]{6}$")
    
    # Facial features
    has_freckles: bool = False
    has_beauty_marks: bool = False
    has_wrinkles: bool = False
    has_moles: bool = False
    
    # Facial hair
    has_beard: bool = False
    has_moustache: bool = False
    has_eyebrows: bool = True
    beard_color: str = Field(default="#8B4513", pattern=r"^#[0-9A-F]{6}$")
    moustache_color: str = Field(default="#8B4513", pattern=r"^#[0-9A-F]{6}$")
    eyebrow_color: str = Field(default="#8B4513", pattern=r"^#[0-9A-F]{6}$")
    beard_length: float = Field(default=0.0, ge=0.0, le=1.0)
    moustache_length: float = Field(default=0.0, ge=0.0, le=1.0)
    eyebrow_length: float = Field(default=0.5, ge=0.0, le=1.0)
    beard_style: BeardStyle = BeardStyle.NONE
    moustache_style: MoustacheStyle = MoustacheStyle.NONE
    eyebrow_style: EyeBrowStyle = EyeBrowStyle.NATURAL
    beard_position: BeardPosition = BeardPosition.NONE
    moustache_position: MoustachePosition = MoustachePosition.NONE
    eyebrow_position: EyeBrowPosition = EyeBrowPosition.NORMAL

class PartnerCreate(PartnerBase):
    user_id: UUID

class PartnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    gender: Optional[Gender] = None
    age: Optional[int] = Field(None, ge=18, le=100)
    skin_tone: Optional[SkinTone] = None
    body_type: Optional[BodyType] = None
    height: Optional[int] = Field(None, ge=120, le=266)
    fitness_level: Optional[FitnessLevel] = None
    
    # Face
    face_shape: Optional[FaceShape] = None
    eye_shape: Optional[EyeShape] = None
    eye_size: Optional[EyeSize] = None
    eye_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    nose_shape: Optional[NoseShape] = None
    nose_size: Optional[NoseSize] = None
    nose_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    hair_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    hair_style: Optional[HairStyle] = None
    mouth_shape: Optional[MouthShape] = None
    teeth_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    lip_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    
    # Ears
    ear_shape: Optional[EarShape] = None
    ear_size: Optional[EarSize] = None
    ear_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    ear_position: Optional[EarPosition] = None
    ear_hair: Optional[EarHair] = None
    ear_hair_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    ear_hair_length: Optional[EarHairLength] = None
    ear_hair_style: Optional[EarHairStyle] = None
    ear_hair_position: Optional[EarHairPosition] = None
    
    # Body proportions
    leg_length: Optional[float] = Field(None, ge=0.0, le=1.0)
    arm_length: Optional[float] = Field(None, ge=0.0, le=1.0)
    torso_length: Optional[float] = Field(None, ge=0.0, le=1.0)
    gluteal_size: Optional[float] = Field(None, ge=0.0, le=1.0)
    chest_size: Optional[float] = Field(None, ge=0.0, le=1.0)
    hand_size: Optional[float] = Field(None, ge=0.0, le=1.0)
    foot_size: Optional[float] = Field(None, ge=0.0, le=1.0)
    waist_size: Optional[float] = Field(None, ge=0.0, le=1.0)
    neck_size: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Nails
    nail_length: Optional[float] = Field(None, ge=0.0, le=1.0)
    nail_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    foot_nail_length: Optional[float] = Field(None, ge=0.0, le=1.0)
    foot_nail_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    
    # Facial features
    has_freckles: Optional[bool] = None
    has_beauty_marks: Optional[bool] = None
    has_wrinkles: Optional[bool] = None
    has_moles: Optional[bool] = None
    
    # Facial hair
    has_beard: Optional[bool] = None
    has_moustache: Optional[bool] = None
    has_eyebrows: Optional[bool] = None
    beard_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    moustache_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    eyebrow_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    beard_length: Optional[float] = Field(None, ge=0.0, le=1.0)
    moustache_length: Optional[float] = Field(None, ge=0.0, le=1.0)
    eyebrow_length: Optional[float] = Field(None, ge=0.0, le=1.0)
    beard_style: Optional[BeardStyle] = None
    moustache_style: Optional[MoustacheStyle] = None
    eyebrow_style: Optional[EyeBrowStyle] = None
    beard_position: Optional[BeardPosition] = None
    moustache_position: Optional[MoustachePosition] = None
    eyebrow_position: Optional[EyeBrowPosition] = None

class ClothingItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    category: str = Field(..., min_length=1, max_length=128)
    sub_category: Optional[str] = Field(None, max_length=128)
    color: str = Field(..., pattern=r"^#[0-9A-F]{6}$")
    size: ClothingSize = ClothingSize.M
    price: float = Field(default=0.0, ge=0.0)
    image_url: Optional[str] = Field(None, max_length=255)
    is_available: bool = True
    is_premium: bool = False
    is_gift: bool = False
    is_bought: bool = True

class ClothingItemCreate(ClothingItemBase):
    pass

class ClothingItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    category: Optional[str] = Field(None, min_length=1, max_length=128)
    sub_category: Optional[str] = Field(None, max_length=128)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    size: Optional[ClothingSize] = None
    price: Optional[float] = Field(None, ge=0.0)
    image_url: Optional[str] = Field(None, max_length=255)
    is_available: Optional[bool] = None
    is_premium: Optional[bool] = None
    is_gift: Optional[bool] = None
    is_bought: Optional[bool] = None

class ClothingItemResponse(ClothingItemBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    bought_at: Optional[datetime] = None
    dropped_at: Optional[datetime] = None
    gifted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class PartnerClothingBase(BaseModel):
    clothing_item_id: UUID
    is_equipped: bool = False
    slot: str = Field(..., min_length=1, max_length=50)

class PartnerClothingCreate(PartnerClothingBase):
    partner_id: UUID

class PartnerClothingUpdate(BaseModel):
    clothing_item_id: Optional[UUID] = None
    is_equipped: Optional[bool] = None
    slot: Optional[str] = Field(None, min_length=1, max_length=50)

class PartnerClothingResponse(PartnerClothingBase):
    id: UUID
    partner_id: UUID
    clothing_item: ClothingItemResponse
    
    class Config:
        from_attributes = True

class PartnerPiercingBase(BaseModel):
    location: PiercingLocation
    jewelry_type: str = Field(..., min_length=1, max_length=50)
    jewelry_material: str = Field(..., min_length=1, max_length=50)
    jewelry_color: str = Field(..., pattern=r"^#[0-9A-F]{6}$")
    size: str = Field(default="medium", max_length=50)

class PartnerPiercingCreate(PartnerPiercingBase):
    partner_id: UUID

class PartnerPiercingUpdate(BaseModel):
    location: Optional[PiercingLocation] = None
    jewelry_type: Optional[str] = Field(None, min_length=1, max_length=50)
    jewelry_material: Optional[str] = Field(None, min_length=1, max_length=50)
    jewelry_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    size: Optional[str] = Field(None, max_length=50)

class PartnerPiercingResponse(PartnerPiercingBase):
    id: UUID
    partner_id: UUID
    
    class Config:
        from_attributes = True

class PartnerTattooBase(BaseModel):
    location: TattooLocation
    tattoo_type: str = Field(..., min_length=1, max_length=50)
    tattoo_style: str = Field(..., min_length=1, max_length=50)
    tattoo_color: str = Field(..., pattern=r"^#[0-9A-F]{6}$")
    size: str = Field(..., min_length=1, max_length=50)
    image_url: Optional[str] = Field(None, max_length=255)

class PartnerTattooCreate(PartnerTattooBase):
    partner_id: UUID

class PartnerTattooUpdate(BaseModel):
    location: Optional[TattooLocation] = None
    tattoo_type: Optional[str] = Field(None, min_length=1, max_length=50)
    tattoo_style: Optional[str] = Field(None, min_length=1, max_length=50)
    tattoo_color: Optional[str] = Field(None, pattern=r"^#[0-9A-F]{6}$")
    size: Optional[str] = Field(None, min_length=1, max_length=50)
    image_url: Optional[str] = Field(None, max_length=255)

class PartnerTattooResponse(PartnerTattooBase):
    id: UUID
    partner_id: UUID
    
    class Config:
        from_attributes = True

class PartnerResponse(PartnerBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    clothing_items: List[PartnerClothingResponse] = []
    piercings: List[PartnerPiercingResponse] = []
    tattoos: List[PartnerTattooResponse] = []
    
    class Config:
        from_attributes = True

# ==================== VALIDATORS ====================

@validator("*_color", pre=True)
def validate_hex_color(cls, v):
    if v and isinstance(v, str):
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in hex format (#RRGGBB)")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Invalid hex color format")
        return v.upper()
    return v

# ==================== UTILITY MODELS ====================

class PartnerCustomizationStats(BaseModel):
    """Estadísticas de personalización del partner"""
    total_clothing_items: int = 0
    total_piercings: int = 0
    total_tattoos: int = 0
    customization_percentage: float = 0.0  # 0.0 to 100.0
    premium_items_count: int = 0
    total_spent: float = 0.0
    
class PartnerPreset(BaseModel):
    """Presets predefinidos para creación rápida de partners"""
    name: str
    description: str
    partner_data: PartnerBase
    
# Common presets
PARTNER_PRESETS = {
    "casual_female": PartnerPreset(
        name="Casual Female",
        description="A casual female partner with default settings",
        partner_data=PartnerBase(
            name="Casual Girl",
            gender=Gender.FEMALE,
            body_type=BodyType.CURVY,
            hair_style=HairStyle.LONG,
            nail_color="#FF69B4"
        )
    ),
    "athletic_male": PartnerPreset(
        name="Athletic Male",
        description="An athletic male partner",
        partner_data=PartnerBase(
            name="Athletic Guy",
            gender=Gender.MALE,
            body_type=BodyType.ATHLETIC,
            fitness_level=FitnessLevel.HIGH,
            hair_style=HairStyle.SHORT,
            has_beard=True,
            beard_style=BeardStyle.STUBBLE
        )
    ),
    "goth_female": PartnerPreset(
        name="Goth Female",
        description="A gothic style female partner",
        partner_data=PartnerBase(
            name="Goth Girl",
            gender=Gender.FEMALE,
            skin_tone=SkinTone.PORCELAIN,
            hair_color="#000000",
            hair_style=HairStyle.LONG,
            lip_color="#8B0000",
            nail_color="#000000"
        )
    )
}

class ClothingCategory(BaseModel):
    """Categorías de ropa disponibles"""
    name: str
    display_name: str
    slots: List[str]
    required: bool = False

# Clothing categories configuration
CLOTHING_CATEGORIES = {
    "tops": ClothingCategory(
        name="tops",
        display_name="Tops",
        slots=["chest"],
        required=True
    ),
    "bottoms": ClothingCategory(
        name="bottoms", 
        display_name="Bottoms",
        slots=["legs"],
        required=True
    ),
    "shoes": ClothingCategory(
        name="shoes",
        display_name="Shoes", 
        slots=["feet"],
        required=True
    ),
    "accessories": ClothingCategory(
        name="accessories",
        display_name="Accessories",
        slots=["head", "neck", "wrist", "hands"],
        required=False
    ),
    "underwear": ClothingCategory(
        name="underwear",
        display_name="Underwear",
        slots=["chest", "hips"],
        required=False
    )
}

class PartnerSearchFilters(BaseModel):
    """Filtros para búsqueda de partners"""
    gender: Optional[Gender] = None
    age_min: Optional[int] = Field(None, ge=18)
    age_max: Optional[int] = Field(None, le=100)
    body_type: Optional[BodyType] = None
    skin_tone: Optional[SkinTone] = None
    hair_style: Optional[HairStyle] = None
    has_tattoos: Optional[bool] = None
    has_piercings: Optional[bool] = None
    fitness_level: Optional[FitnessLevel] = None