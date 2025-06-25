from src.pallet import CargoType, Pallet
from src.reference_book import ReferenceBook


class CargoPacker:
    @staticmethod
    def pack_cargos(cargos: list[CargoType]) -> list[Pallet]:
        """
        Packs a list of cargos into pallets based on the reference book.

        Args:
            cargos (list[CargoType]): List of cargo types to be packed.

        Returns:
            list[Pallet]: List of pallets containing the packed cargos.
        """
        reference_book = ReferenceBook()
        pallet_types = reference_book.get_pallet_types()
        pallet_types = sorted(pallet_types.values(), key=lambda x: x.width)

        pallets = []
        for cargo in cargos:
            found_pallet = False

            for pallet_type in pallet_types:
                if (cargo.width <= pallet_type.width
                    and cargo.length <= pallet_type.length
                    or cargo.length <= pallet_type.width
                        and cargo.width <= pallet_type.length):
                    pallet = Pallet(pallet_type=pallet_type, cargo=cargo)
                    pallets.append(pallet)
                    found_pallet = True
                    break

            if not found_pallet:
                raise ValueError("No suitable pallet found "
                                 f"for cargo {cargo.cargo_type_id}")

        return pallets
