"""Reference metadata for the 85 classes described in the project report."""

from model_utils import split_class_name


ORDER_RANGES = {
    "Galliformes": range(1, 5),
    "Anseriformes": range(5, 9),
    "Podicipediformes": range(9, 10),
    "Phoenicopteriformes": range(10, 11),
    "Pterocliformes": range(11, 12),
    "Caprimulgiformes": range(12, 14),
    "Cuculiformes": range(14, 17),
    "Gaviiformes": range(17, 18),
    "Pelecaniformes": range(18, 20),
    "Suliformes": range(20, 22),
    "Columbiformes": range(22, 25),
    "Gruiformes": range(25, 27),
    "Ciconiiformes": range(27, 31),
    "Otidiformes": range(31, 33),
    "Charadriiformes": range(33, 38),
    "Strigiformes": range(38, 40),
    "Accipitriformes": range(40, 46),
    "Trogoniformes": range(46, 47),
    "Bucerotiformes": range(47, 49),
    "Coraciiformes": range(49, 51),
    "Piciformes": range(51, 53),
    "Falconiformes": range(53, 55),
    "Psittaciformes": range(55, 57),
    "Passeriformes": range(57, 86),
}

FAMILY_RANGES = {
    "Phasianidae": range(1, 5), "Anatidae": range(5, 9),
    "Podicipedidae": range(9, 10), "Phoenicopteridae": range(10, 11),
    "Pteroclidae": range(11, 12), "Caprimulgidae": range(12, 14),
    "Cuculidae": range(14, 17), "Gaviidae": range(17, 18),
    "Ardeidae": range(18, 20), "Phalacrocoracidae": range(20, 22),
    "Columbidae": range(22, 25), "Gruidae": range(25, 27),
    "Ciconiidae": range(27, 31), "Otididae": range(31, 33),
    "Laridae": range(33, 35), "Charadriidae": range(35, 37),
    "Ibidorhynchidae": range(37, 38), "Tytonidae": range(38, 39),
    "Strigidae": range(39, 40), "Accipitridae": range(40, 46),
    "Trogonidae": range(46, 47), "Bucerotidae": range(47, 49),
    "Alcedinidae": range(49, 51), "Megalaimidae": range(51, 52),
    "Picidae": range(52, 53), "Falconidae": range(53, 55),
    "Psittacidae": range(55, 57), "Paridae": range(57, 59),
    "Scotocercidae": range(59, 61), "Paradoxornithidae": range(61, 63),
    "Zosteropidae": range(63, 65), "Timaliidae": range(65, 67),
    "Alcippeidae": range(67, 68), "Pellorneidae": range(68, 69),
    "Leiotrichidae": range(69, 74), "Muscicapidae": range(74, 77),
    "Irenidae": range(77, 78), "Dicaeidae": range(78, 80),
    "Nectariniidae": range(80, 82), "Ploceidae": range(82, 84),
    "Emberizidae": range(84, 86),
}

GLOBAL_STATUS = {
    1: "VU", 2: "VU", 5: "VU", 6: "CR", 26: "VU", 29: "EN",
    30: "VU", 31: "CR", 32: "CR", 33: "VU", 34: "EN", 41: "CR",
    42: "EN", 43: "EN", 45: "EN", 47: "VU", 48: "VU", 50: "EN",
    75: "VU", 85: "CR",
}

NEPAL_STATUS = {
    2: "EN", 3: "VU", 6: "CR", 7: "EN", 8: "VU", 11: "VU",
    12: "EN", 18: "EN", 19: "EN", 22: "VU", 23: "EN", 24: "CR",
    25: "VU", 26: "VU", 27: "CR", 28: "EN", 29: "CR", 30: "VU",
    31: "CR", 32: "CR", 33: "CR", 34: "CR", 35: "VU", 37: "EN",
    38: "CR", 39: "CR", 40: "VU", 41: "CR", 42: "VU", 43: "VU",
    44: "CR", 45: "CR", 46: "EN", 47: "EN", 49: "EN", 50: "CR",
    51: "CR", 52: "CR", 53: "EN", 54: "CR", 55: "CR", 56: "VU",
    57: "EN", 58: "CR", 59: "VU", 60: "CR", 61: "VU", 62: "VU",
    63: "VU", 64: "CR", 65: "CR", 66: "EN", 68: "EN", 69: "VU",
    70: "VU", 71: "CR", 72: "CR", 73: "EN", 74: "VU", 75: "VU",
    76: "CR", 77: "CR", 78: "CR", 79: "CR", 80: "CR", 81: "EN",
    82: "VU", 83: "CR", 84: "VU", 85: "CR",
}

STATUS_NAMES = {
    "CR": "Critically Endangered",
    "EN": "Endangered",
    "VU": "Vulnerable",
    "-": "Not listed as threatened in the project table",
}

ORDER_STORIES = {
    "Galliformes": ("Forest & ground birds", "Mostly strong-legged terrestrial birds such as pheasants and francolins."),
    "Anseriformes": ("Waterfowl", "Ducks and their relatives, closely connected to lakes, rivers and wetlands."),
    "Podicipediformes": ("Diving waterbirds", "Grebes are compact swimmers with lobed toes, short wings and strong underwater movement."),
    "Phoenicopteriformes": ("Flamingos", "Long-legged, web-footed waterbirds adapted to feeding in shallow saline or alkaline wetlands."),
    "Pterocliformes": ("Sandgrouse", "Ground-dwelling birds whose cryptic plumage blends with open, dry and high-altitude landscapes."),
    "Caprimulgiformes": ("Nightjars", "Mostly dusk- or night-active birds with cryptic plumage, long wings and a wide gape for catching insects."),
    "Cuculiformes": ("Cuckoos", "Often long-tailed birds with curved bills; some species are better detected by voice than by sight."),
    "Gaviiformes": ("Loons", "Streamlined diving birds with dagger-like bills and legs positioned far back for underwater propulsion."),
    "Pelecaniformes": ("Herons & allies", "Water-associated birds that include stealthy, long-billed hunters of wetlands and river margins."),
    "Suliformes": ("Cormorants & allies", "Dark, streamlined fish-eaters that pursue prey underwater and often rest with wings spread."),
    "Columbiformes": ("Pigeons & doves", "Compact seed- and fruit-eating birds with small heads, short bills and powerful direct flight."),
    "Gruiformes": ("Cranes & rails", "A diverse order ranging from secretive wetland rails to tall, long-legged cranes."),
    "Ciconiiformes": ("Storks", "Large wetland birds with long legs, long necks and substantial bills used to capture animal prey."),
    "Otidiformes": ("Bustards & floricans", "Long-legged birds of open grassland, many of which depend on large, undisturbed habitats."),
    "Charadriiformes": ("Shore & river birds", "A varied order that includes terns, lapwings and specialist river birds."),
    "Accipitriformes": ("Raptors", "Large daytime birds of prey, including eagles and vultures."),
    "Passeriformes": ("Perching birds", "The largest bird order, covering many songbirds and small forest species."),
    "Strigiformes": ("Owls", "Predatory birds adapted for quiet flight and often for low-light activity."),
    "Trogoniformes": ("Trogons", "Colourful forest birds with compact bodies, broad tails and a distinctive toe arrangement."),
    "Bucerotiformes": ("Hornbills", "Large forest birds recognised by their long bills, often topped by a casque, and important fruit-eating habits."),
    "Coraciiformes": ("Kingfishers & allies", "Often vividly coloured birds with strong bills, including species associated with forest and water."),
    "Piciformes": ("Woodpeckers & barbets", "Mostly tree-associated birds; many have strong bills and feet adapted for climbing or gripping."),
    "Falconiformes": ("Falcons", "Fast-flying raptors with pointed wings, hooked bills and strong talons."),
    "Psittaciformes": ("Parrots", "Social birds with strong curved bills and grasping feet, often associated with woodland and forest."),
}


def _lookup(number, groups, fallback="Other"):
    return next((name for name, numbers in groups.items() if number in numbers), fallback)


def build_catalog(class_names):
    catalog = []
    for raw_name in class_names:
        number, common, scientific = split_class_name(raw_name)
        class_number = int(number)
        catalog.append(
            {
                "number": class_number,
                "common_name": common.strip(),
                "scientific_name": scientific.strip(),
                "order": _lookup(class_number, ORDER_RANGES),
                "family": _lookup(class_number, FAMILY_RANGES),
                "global_status": GLOBAL_STATUS.get(class_number, "-"),
                "nepal_status": NEPAL_STATUS.get(class_number, "-"),
            }
        )
    return sorted(catalog, key=lambda bird: bird["number"])
