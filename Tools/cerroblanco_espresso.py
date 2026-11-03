""" Cerro Blanco's cafe espresso machine in the scene: one placed copy of espresso_machine_v2 on the cafe counter, where the fit-out used to draw a steel box, a renderer only, as the old one had
no collision. Its working front faces plan north, toward the barista behind the counter, which is world yaw 0. See docs/notes and Sources/CerroBlanco/espresso-machine-v2/. """
import map_kit as K

MODEL = "models/maps/cerroblanco/espresso_machine_v2/machine.vmdl"
AT = ( 575.0, 615.0, 42.0 )  # Plan ( e, n, z ): the counter's top at 42.


def scene_group( ids, at=AT ):
    world = tuple( float( x ) for x in K.to_world( at ) )
    key = f"espresso-machine/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
    return K.game_object( ids, "Espresso Machine", key, world, components=[
        K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
    ] )
