import {
  Card,
  CardContent, CardMedia,
  Grid, Chip,
  Typography
} from "@material-ui/core"
import React from "react"
import {connect as reduxConnect} from "react-redux"
import {RouteComponentProps} from "react-router-dom"
import {withRouter} from "react-router"
import {FormattedMessage} from "react-intl";

import {RootState} from "../../stores/rootReducer"
import {DispatchedReduxThunkActionCreator} from "../../utils/types"
import {Content} from "../components/Content/style"
import {Sidebar} from "../components/Sidebar"
import {Organisation} from "../../stores/organisations/reducer"
import {fetchOrganisations} from "../../stores/organisations/effects"
import {useStyles} from "./style"
import {ManageRoomButtons} from "../components/ManageRoomButtons"

interface OrganisationsProps {
  organisations: Organisation[]
  fetchOrganisations: DispatchedReduxThunkActionCreator<Promise<void>>
  url: string
}

function mapStateToProps(state: RootState) {
  return {
    organisations: state.organisations,
    url: state.room.props.url,
  }
}

const mapDispatchToProps = {
  fetchOrganisations
}

function OrganisationsConnector (props: OrganisationsProps & RouteComponentProps) {
  const { organisations, fetchOrganisations, url } = props
  if (!organisations) {
    fetchOrganisations()
  }
  const classes = useStyles()
  return (
    <Grid container>
      <Content>
        <Typography component="h1">
          <FormattedMessage id="Represented organisations" />
        </Typography>
        {organisations && organisations.length > 0 && (
        <Grid container spacing={2}>
          {organisations.map((organisation, index) => (
          <Grid item key={index} sm={6} className="now">
            <Card className={classes.card}>
            <CardMedia
                component="img"
                alt={organisation.props.name}
                height="100"
                image={organisation.props.imageUrl}
                title={organisation.props.name}
              />
              <CardContent>
                <Typography component="span">{organisation.props.name}</Typography>
                <Typography component="p">{organisation.props.description}</Typography>
                <Typography component="span">{organisation.props.topics.join(", ")}</Typography>
                <Typography component="span">{organisation.props.location}</Typography>
              </CardContent>
            </Card>
          </Grid>
          ))}
        </Grid>
        )
        || <Typography><FormattedMessage id="No represented organisations."/></Typography>
        }
        <ManageRoomButtons />
      </Content>
      {url && <Sidebar url={url} />}
    </Grid>
  )
}

export const Organisations = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(OrganisationsConnector)
)
