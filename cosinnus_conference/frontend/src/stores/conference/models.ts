import {Room, RoomJson} from "../room/models"

export interface ConferenceJson {
  id: number
  name: string
  description: string
  rooms: RoomJson[]
  management_urls: {
    manage_conference: string
    manage_rooms: string
    manage_events: string
  }
  theme_color: string
  dates: string[]
}

export interface ConferenceProps {
  id: number
  name: string
  description: string
  rooms: Room[]
  managementUrls: {
    manageConference: string
    manageRooms: string
    manageEvents: string
  }
  themeColor: string
  dates: string[]
}

export class Conference {
  props: ConferenceProps

  public constructor(props: ConferenceProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {User} - Conference object
   */
  public static fromJson(json: ConferenceJson) : Conference {
    const props: ConferenceProps = {
      id: json.id,
      name: json.name,
      description: json.description,
      rooms: [],
      managementUrls: {
        manageConference: json.management_urls.manage_conference,
        manageRooms: json.management_urls.manage_rooms,
        manageEvents: json.management_urls.manage_events,
      },
      themeColor: json.theme_color,
      dates: json.dates,
    }
    if (json.rooms != null) {
      json.rooms.forEach((room: any) => {
        props.rooms.push(Room.fromJson(room))
      })
    }

    return new Conference(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {ConferenceJson} - object in JSON format
   */
  toJson() : ConferenceJson {
    const props = this.props
    const rooms: RoomJson[] = []
    if (props.rooms != null) {
      props.rooms.forEach((room: any) => {
        rooms.push(room.toJson())
      })
    }
    return {
      id: props.id,
      name: props.name,
      description: props.description,
      rooms: rooms,
      management_urls: {
        manage_conference: props.managementUrls.manageConference,
        manage_rooms: props.managementUrls.manageRooms,
        manage_events: props.managementUrls.manageEvents,
      },
      theme_color: props.themeColor,
      dates: props.dates,
    }
  }

  /**
   * Get theme color
   *
   * @returns {string} Color including # or undefined if none
   */
  getThemeColor() : string {
    return this.props.themeColor && '#' + this.props.themeColor || undefined
  }
}
