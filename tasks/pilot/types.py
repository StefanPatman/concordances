from enum import IntEnum


class SubstitutionModel(IntEnum):
    KIMURA = 0, "Kimura-2P", "Kimura-2P (K80)"
    JC = 1, "Jukes-Cantor", "Jukes-Cantor (JC69)"
    TN = 2, "Tamura-Nei", "Tamura-Nei (TN93)"
    SIMPLE = 3, "Simple Distance", "Simple Distance (p-distances)"

    def __new__(cls, value, label, description):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        obj.description = description
        return obj

    def __str__(self):
        return f"{self.description} ({self.value})"
