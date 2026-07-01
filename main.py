from tools.system.system_info import SystemInfoTool


def main():
    tool = SystemInfoTool()
    result = tool.execute()

    print("=" * 45)
    print(f"{result.title:^45}")
    print("=" * 45)

    for key, value in result.data.items():

        if isinstance(value, list):
            print(f"{key:<20}: {value[0]}")

            for item in value[1:]:
                print(f"{'':20}  {item}")

        else:
            print(f"{key:<20}: {value}")

    print()
    print(result.explanation)

if __name__ == "__main__":
    main()