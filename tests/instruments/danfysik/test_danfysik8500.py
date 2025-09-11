from pymeasure.test import expected_protocol

from pymeasure.instruments.danfysik import Danfysik8500


init_comm = [(b"ERRT", None), (b"UNLOCK", None)]


def test_init():
    with expected_protocol(Danfysik8500, init_comm):
        pass
