from base.objects import Hospital, HospitalSystem


def main():
    hospital_system = HospitalSystem(
        name="Danny's Hospital", hospitals=[Hospital(name="L"), Hospital(name="W")]
    )


if __name__ == "__main__":
    main()
